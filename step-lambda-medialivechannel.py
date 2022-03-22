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

    max_resolution = "HD"
    max_bitrate = "MAX_10_MBPS"
    input_codec = "AVC"
    loglevel = "DISABLED"


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
            create_channel_response = eml_client.create_channel(ChannelClass=pipeline,InputAttachments=channel_input_attachments,Destinations=destinations_template,EncoderSettings=encoder_settings,InputSpecification=input_specs,LogLevel=loglevel,Name=channel_name,RoleArn=role_arn)
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
                new_item_list.clear()



                for i in range(0,len(value)):

                    dynamodb_item_list = dict()
                    dynamodb_item_list.clear()

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

    # initialize medialive boto3 client
    region = json_item['Region']
    eml_client = boto3.client('medialive', region_name=region)

    if task == "create":

        medialive_db_item = dict()

        pipeline = json_item['Pipeline']

        # task = event['detail']['task']
        # channels = event['detail']['channels']
        # channel_data = event['detail']['channel_data']
        # deployment_name = event['detail']['name']
        # dynamodb_table_name

        jpg_bucket = os.environ['S3Bucket']
        jpg_base_path = '/'.join(os.environ['FrameCaptureToJpgPath'].split("/")[0:-1])

        # Get MediaLive templates to json dictionaries
        template_bucket = os.environ['S3Bucket']

        mux_hd_avc = get_template_from_s3(template_bucket,os.environ['MuxHDTemplate'])
        mux_sd_avc = get_template_from_s3(template_bucket,os.environ['MuxSDTemplate'])
        ott_hd_avc = get_template_from_s3(template_bucket,os.environ['OttSDTemplate'])
        ott_sd_avc = get_template_from_s3(template_bucket,os.environ['OttSDTemplate'])

        default_template = ott_sd_avc

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

            for channel in range(1,int(channels)+1):

                input_specs = dict()
                input_specs['Codec'] = input_codec
                input_specs['MaximumBitrate'] = max_bitrate
                input_specs['Resolution'] = max_resolution

                medialive_channel = json_item["MediaLive"][str(channel)]

                encoder_settings = default_template['EncoderSettings']
                destinations_template = default_template['Destinations']

                # InputAttachmentName, InputId, InputSettings
                channel_input_attachments = []
                for ia in range(0,len(medialive_channel['Input_Attachments'])):

                    input_properties = {
                        "InputAttachmentName":medialive_channel['Input_Attachments'][ia]['Name'],
                        "InputId":medialive_channel['Input_Attachments'][ia]['Id'],
                        "InputSettings":{
                            "SourceEndBehavior":""
                        }

                    }


                    if "continue" in medialive_channel['Input_Attachments'][ia]['Name'].lower():
                        input_properties['InputSettings']['SourceEndBehavior'] = "LOOP"
                    else:
                        input_properties['InputSettings']['SourceEndBehavior'] = "CONTINUE"

                    if medialive_channel['Input_Attachments'][ia]['Type'] == "URL_PULL" and "m3u8" in medialive_channel['Input_Attachments'][ia]['Sources'][0]['Url']:
                        input_properties['InputSettings']['NetworkInputSettings'] = {"HlsInputSettings":{"BufferSegments":3,"Scte35Source":"MANIFEST"}}

                    channel_input_attachments.append(input_properties)

                # construct medialive event outputs
                for destination in destinations_template:
                    if 'MediaPackageSettings' in destination: # This output is to MediaPackage
                        LOGGER.debug("This is MediaPackage destination - EMP: %s" % (destination))

                        mediapackage_id = json_item['MediaPackage'][str(channel)]['Channel_Name']

                        destination['MediaPackageSettings'][0]['ChannelId'] = mediapackage_id # Path to put MediaPackage Channel ID

                    elif 'Settings' in destination:
                        LOGGER.debug("This is S3 Destination - JPG: %s" % (destination))
                        # ottauto/deployments
                        jpg_full_path = "s3://%s/%s/%s/%s/status" % (jpg_bucket,jpg_base_path,deployment_name,channel)
                        LOGGER.debug("MediaLive Channel %s outputting JPG to %s" % (channel, jpg_full_path))
                        destination['Settings'][0]['Url'] = jpg_full_path # Path to s3 published JPG

                channel_name = "%s_%02d" % (deployment_name,channel)


                medialive_create_channel_response = createEMLChannel()

                if len(exceptions) > 0:
                    errorOut()

                channel_arn = medialive_create_channel_response['Channel']['Arn']

                # Update json item
                json_item["MediaLive"][str(channel)]['Channel_Name'] = channel_name
                json_item["MediaLive"][str(channel)]['Channel_Arn'] = channel_arn


        eml_dict_to_dynamo = dict()
        json_to_dynamo(eml_dict_to_dynamo,json_item)

        putItem(eml_dict_to_dynamo)
        if len(exceptions) > 0:
            return errorOut()
        else:
            event['status'] = "Completed creation of MediaLive channels with no issues"
            return event


    else: # this is delete

        if event['detail']['delete_tasks']['medialive_channels'] == 0:

            medialive_channels = json_item['MediaLive']

            delete_exceptions = []
            for channel in list(medialive_channels.keys()):

                try:
                    channel_arn = medialive_channels[channel]['Channel_Arn']
                    channel_id = channel_arn.split(":")[-1]
                    deleteEMLChannel(channel_id)

                except:

                    delete_exceptions.append("Unable to get MediaLive Channel Arn info from DB for channel : %s " % (channel_id))

            event['status'] = "Completed deletion of MediaLive Channels"
            event['eml_channel_delete_exceptions'] = delete_exceptions
            event['detail']['delete_tasks']['medialive_channels'] = 1

        return event