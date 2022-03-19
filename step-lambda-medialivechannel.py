import json
import boto3
import os
import logging
import datetime
import re
import uuid
import base64

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

unique_timestamp = str(datetime.datetime.now().strftime('%s'))
exceptions = []
role_arn = os.environ['RoleArn']

#json.loads(json.dumps(response, default = lambda o: f"<<non-serializable: {type(o).__qualname__}>>"))


def lambda_handler(event, context):

    task = event['detail']['task']
    channels = event['detail']['channels']
    deployment_name = event['detail']['name']
    dynamodb_table_name= event['detail']['dynamodb_table_name']
    channel_data = event['detail']['channel_data']


    ###
    ### FUNCTIONS
    ###

    def api_response(response_code,response_body):
        return {
            'statusCode': response_code,
            'body': json.dumps(response_body)
        }

    def putItem(updated_item):
        # Create DB Item for deployment
        LOGGER.info("Attempting to update item in DB now...")

        try:
            put_item_response = db_client.put_item(TableName=dynamodb_table_name,Item=updated_item)
            LOGGER.debug("DynamoDB Put Item response: %s" % (put_item_response))
        except Exception as e:
            LOGGER.error("Unable to create item in database. Please try again later, response : %s " % (e))
            exceptions.append(e)
            return e
        LOGGER.info("Completed DB update for deployment")
        return put_item_response

    def getItem():
        try:
            key = {'Group_Name':{'S':deployment_name}}
            response = db_client.get_item(TableName=dynamodb_table_name,Key=key)
            LOGGER.debug("dynamodb get item response : %s " % (response))
        except Exception as e:
            exceptions.append("Unable to get item information from DynamoDB, got exception:  %s " % (e))
            LOGGER.error("Unable to get item information from DynamoDB, got exception:  %s " % (e))
        return response

    def errorOut():
        event['status'] = exceptions
        raise Exception("Unable to complete function : %s" % (event))
        ### NEED TO raise exception here!
        return event


    #########


    def createEMLChannel():
        LOGGER.info("Attempting to create MediaLive Channel : %s " % (channel_name))

        # Create Channel
        try:
            create_channel_response = eml_client.create_channel(ChannelClass=pipeline,InputAttachments=input_attachments,Destinations=destinations_template,EncoderSettings=encoder_settings,InputSpecification={'Codec':input_codec,'MaximumBitrate':max_bitrate,'Resolution':max_resolution},LogLevel=loglevel,Name=channel_name,RoleArn=role_arn)
        except Exception as e:
            LOGGER.error("Unable to create channel %s, got exception : %s" % (channel_name,e))
            exceptions.append("Unable to create channel, got exception : %s" % (e))
            create_channel_response = "Unable to create channel, got exception : %s" % (e)
        LOGGER.info("Done Creating MediaLive Channel : %s " % (channel_name))
        return create_channel_response

    def deleteEMLChannel(channel_id):
        LOGGER.info("Attempting to delete MediaLive Channel : %s " % (channel_id))

        # Delete Channel
        try:
            delete_channel_response = eml_client.delete_channel(ChannelId=channel_id)
        except Exception as e:
            msg = "Unable to delete channel %s, got exception : %s" % (channel_id,e)
            LOGGER.error(msg)
            delete_exceptions.append(msg)
            return msg
        return delete_channel_response

    def get_template_from_s3(bucket,key):
        LOGGER.info("Attempting to get channel template json from S3: %s " % (key))

        # s3 boto3 client initialize
        s3_client = boto3.client('s3', region_name=region)

        try:
            s3_raw_response = s3_client.get_object(Bucket=bucket,Key=key)
        except Exception as e:
            msg = "Unable to get template %s from S3, got exception : %s" % (key,e)
            LOGGER.error(msg)
            exceptions.append(msg)
            return msg

        return json.loads(s3_raw_response['Body'].read())


    # JSON_TO_DYNAMODB_BUILDER
    def json_to_dynamo(dicttopopulate,my_dict):
        for k,v in my_dict.items():

            if isinstance(v,dict):
                dynamodb_item_subdict = dict()
                json_to_dynamo(dynamodb_item_subdict,v)

                v = dynamodb_item_subdict
                dicttopopulate.update({k:{"M":v}})

            elif isinstance(v,str):
                dicttopopulate.update({k:{"S":v}})
            elif isinstance(v,list):

                new_item_list = []
                for i in range(0,len(v)):
                    dynamodb_item_list = dict()
                    json_to_dynamo(dynamodb_item_list,v[i])

                    #v[i] = {"M":dynamodb_item_list}
                    new_item_list.append({"M":dynamodb_item_list})

                dicttopopulate.update({k:{"L":new_item_list}})

    # DYNAMODB_JSON_DECONSTRUCTOR
    def dynamo_to_json(dicttopopulate,my_dict):
        for k,v in my_dict.items():

            value_type = list(my_dict[k].keys())[0]

            if value_type == "M":
                value = my_dict[k][value_type]

                # for i in range(0,len(value)):
                dynamodb_item_m = dict()
                dynamo_to_json(dynamodb_item_m,value)
                #     v = dynamodb_item_m

                value.update(dynamodb_item_m)
                dicttopopulate.update({k:value})

            elif value_type == "S":
                value = my_dict[k][value_type]
                dicttopopulate.update({k:value})

            elif value_type == "L": # list
                value = my_dict[k][value_type]

                new_item_list = []

                dynamodb_item_list = dict()
                for i in range(0,len(value)):

                    dynamo_to_json(dynamodb_item_list,value[i])

                new_item_list.append(dynamodb_item_list)

                dicttopopulate.update({k:new_item_list})

            elif k == "M":

                dynamodb_item_m = dict()
                dynamo_to_json(dynamodb_item_m,v)
                v = dynamodb_item_m
                dicttopopulate.update(v)

    ###
    ### FUNCTIONS
    ###

    exceptions.clear()

    # Call DynamoDB to get the deployment information - then convert to json
    db_client = boto3.client('dynamodb')
    try:
        db_item = getItem()['Item']
    except Exception as e:
        LOGGER.error("DB Item doesn't appear to be in DynamoDB table, got exception : %s" % (e))
        raise Exception("DB Item doesn't appear to be in DynamoDB table, got exception : %s" % (e))

    json_item = dict()
    dynamo_to_json(json_item,db_item)

    if task == "create":

        medialive_db_item = dict()

        pipeline = json_item['Pipeline']
        region = json_item['Region']

        # initialize medialive boto3 client
        eml_client = boto3.client('medialive', region_name=region)

        # task = event['detail']['task']
        # channels = event['detail']['channels']
        # channel_data = event['detail']['channel_data']
        # deployment_name = event['detail']['name']
        # dynamodb_table_name


        # Get MediaLive templates to json dictionaries
        template_bucket = os.environ['S3Bucket']

        mux_hd_avc = get_template_from_s3(template_bucket,os.environ['MuxHDTemplate'])
        mux_sd_avc = get_template_from_s3(template_bucket,os.environ['MuxSDTemplate'])
        ott_hd_avc = get_template_from_s3(template_bucket,os.environ['OttSDTemplate'])
        ott_sd_avc = get_template_from_s3(template_bucket,os.environ['OttSDTemplate'])

        if len(exceptions) > 0:

            return errorOut()

        channel_data = []
        if isinstance(channel_data,dict):

            # This includes user input data from the UI

            # check first to see if copy is true
            if len(channel_data['copy']) > 0:

                LOGGER.info("This group will copy settings from group : %s " % (channel_data['copy']))
                #
                #
                # Need a copy function here to copy from another group_name. Copy all settings but extract input settings for each channel from channel_data
                #
                #

            else: # no copy

                LOGGER.info("This group will not copy from an existing group")

                if channel_data['mux']['create'] == True:

                    LOGGER.info("This group will be a statmux group")
                    #
                    #
                    # build in logic to create a statmux group along with each channel
                    #
                    #
                    # after create, write to dynamo with published settings under MediaLive/channnel/mux/[mux channel stuff]
                    #
                    #

                ## regardless we come here to create the ott output
                LOGGER.info("Starting creation of OTT channels for this group")
                LOGGER.info("Defaulting to create SD OTT channels only")


                ## Clean exit of the function down here

        else:

            ## No user data sent through , just do an OTT group
            LOGGER.info("No granular details sent with group create. Creating OTT channels only")
            LOGGER.info("Defaulting to create SD OTT channels only")

            return "..yeah.."

            #
            #
            # Need to just build an output here. no channel_data to pull from, do a cookie cutter channel creation
            #
            #


    else: # this is delete

        return json_item

        medialive_channels = json_item['MediaLive']

        deleted_channels = []
        failed_deleted_channels = []
        for channel in list(medialive_channels.keys()):

            channel_id = medialive_channels[channel]['ChannelId']

            # send to channel delete
            # delete function
            # if no exception, add to deleted_channels list

            # catch exceptions but dont error

            # add status for MediaLive inputs to use
            event['medialive_channels_deleted'] = []
            event['medialive_channel_delete_failed'] = failed_deleted_channels