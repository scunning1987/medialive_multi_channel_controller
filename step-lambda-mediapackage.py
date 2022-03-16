import json
import boto3
import os
import logging
import datetime
import re
import uuid

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

unique_timestamp = str(datetime.datetime.now().strftime('%s'))
exceptions = []
#json.loads(json.dumps(response, default = lambda o: f"<<non-serializable: {type(o).__qualname__}>>"))


def lambda_handler(event, context):

    task = event['detail']['task']
    channels = event['detail']['channels']
    deployment_name = event['detail']['name']
    dynamodb_table_name= event['detail']['dynamodb_table_name']


    ###
    ### FUNCTIONS
    ###
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
            raise Exception("Unable to get item information from DynamoDB, got exception:  %s " % (e))
        return response

    def errorOut():
        event['status'] = exceptions
        raise Exception("Unable to complete MediaPackage task : %s" % (event) )
        ### NEED TO raise exception here!
        return event


    #########

    def create_mediapackage_channel(channel_name):
        LOGGER.info("MediaPackage : Creating channel : %s " % (channel_name))

        # create MediaPackage channel here
        try:
            response = emp_client.create_channel(Description=deployment_name,Id=channel_name)
            LOGGER.debug("Channel creation response : %s " % (response))
        except Exception as e:
            LOGGER.error("Error creating MediaPackage channel - %s , got exception - %s " % (channel_name,e))
            exceptions.append("Error creating MediaPackage channel - %s " % (channel_name))
            return "Error creating MediaPackage channel - %s , got exception - %s " % (channel_name,e)
        return response

    def create_mediapackage_endpoint(channel_name):
        LOGGER.info("Creating origin endpoints for channel : %s " % (str(channel_name)))
        # create MediaPackage endpoint here

        # with open('hls_endpoint_template.json', 'r') as f:
        #     hlstemplate_string = f.read()
        # hlstemplate = json.loads(hlstemplate_string)
        # with open('dash_endpoint_template.json', 'r') as f:
        #     dashtemplate_string = f.read()
        # dashtemplate = json.loads(dashtemplate_string)
        # with open('mss_endpoint_template.json', 'r') as f:
        #     msstemplate_string = f.read()
        # msstemplate = json.loads(msstemplate_string)

        hlstemplate = {
            "AdMarkers": "PASSTHROUGH",
            "AdsOnDeliveryRestrictions": "NONE",
            "IncludeIframeOnlyStream": false,
            "PlaylistType": "NONE",
            "PlaylistWindowSeconds": 60,
            "ProgramDateTimeIntervalSeconds": 60,
            "SegmentDurationSeconds": 6,
            "UseAudioRenditionGroup": false
        }

        endpoint_exceptions = 0

        try:
            endpoint_id = channel_name + "_" + uuid.uuid4().hex
            response = emp_client.create_origin_endpoint(ChannelId=channel_name,HlsPackage=hlstemplate,Origination='ALLOW',Id=endpoint_id,ManifestName='index',Tags={'Usage': 'Dish'})
            LOGGER.debug("Origin Endpoint Creation Response -HLS : %s" % (response))
            endpoints.append({'type':'hls','url':response['Url'],'id':response['Id']})
        except Exception as e:
            LOGGER.error("Error creating Origin endpoint for channel - %s , got exception - %s " % (channel_name,e))
            exceptions.append("Error creating Origin endpoints for channel - %s , got exception - %s " % (channel_name,e))
            endpoint_exceptions += 1

        # try:
        #     endpoint_id = channel_name + "_" + uuid.uuid4().hex
        #     response = emp_client.create_origin_endpoint(ChannelId=channel_name,DashPackage=dashtemplate,Origination='ALLOW',Id=endpoint_id,ManifestName='index',Tags={'Usage': 'Charter'})
        #     LOGGER.debug("Origin Endpoint Creation Response -DASH : %s" % (response))
        #     endpoints.append({'M':{'type':{'S':'dash'},'url':{'S':response['Url']},'id':{'S':response['Id']}}})
        # except Exception as e:
        #     LOGGER.error("Error creating Origin endpoint for channel - %s , got exception - %s " % (channel_name,e))
        #     exceptions.append("Error creating Origin endpoints for channel - %s , got exception - %s " % (channel_name,e))
        #     endpoint_exceptions += 1
        # try:
        #     endpoint_id = channel_name + "_" + uuid.uuid4().hex
        #     response = emp_client.create_origin_endpoint(ChannelId=channel_name,MssPackage=msstemplate,Origination='ALLOW',Id=endpoint_id,ManifestName='index',Tags={'Usage': 'Charter'})
        #     LOGGER.debug("Origin Endpoint Creation Response -MSS : %s" % (response))
        #     endpoints.append({'M':{'type':{'S':'mss'},'url':{'S':response['Url']},'id':{'S':response['Id']}}})
        # except Exception as e:
        #     LOGGER.error("Error creating Origin endpoint for channel - %s , got exception - %s " % (channel_name,e))
        #     exceptions.append("Error creating Origin endpoints for channel - %s , got exception - %s " % (channel_name,e))
        #     endpoint_exceptions += 1
        if endpoint_exceptions > 0:
            LOGGER.error("Error creating %s Origin endpoint(s) for channel - %s , got exception(s) - %s " % (str(endpoint_exceptions),channel_name,exceptions))
            return ""
        else:
            LOGGER.info("Successfully created endpoints for channel %s " % (channel_name))
            return endpoints


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
                for i in range(0,len(v)):
                    dynamodb_item_list = dict()
                    json_to_dynamo(dynamodb_item_list,v[i])

                    v[i] = {"M":dynamodb_item_list}

                dicttopopulate.update({k:{"L":v}})

    # DYNAMODB_JSON_DECONSTRUCTOR
    def dynamo_to_json(dicttopopulate,my_dict):
        for k,v in my_dict.items():

            value_type = list(my_dict[k].keys())[0]

            if value_type == "M":
                value = my_dict[k][value_type]

                for i in range(0,len(value)):
                    dynamodb_item_m = dict()
                    dynamo_to_json(dynamodb_item_m,value)
                    v = dynamodb_item_m

                value.update(dynamodb_item_m)
                dicttopopulate.update({k:value})

            elif value_type == "S":
                value = my_dict[k][value_type]
                dicttopopulate.update({k:value})

            elif value_type == "L": # list
                value = my_dict[k][value_type]

                for i in range(0,len(value)):
                    dynamodb_item_list = dict()
                    dynamo_to_json(dynamodb_item_list,value[i])

                    value[i] = dynamodb_item_list

                dicttopopulate.update({k:value})
            elif k == "M":

                dynamodb_item_m = dict()
                dynamo_to_json(dynamodb_item_m,v)
                v = dynamodb_item_m
                dicttopopulate.update(v)

    ###
    ### FUNCTIONS
    ###

    exceptions.clear()

    # Call DynamoDB to get the deployment information
    db_client = boto3.client('dynamodb')
    db_item = getItem()['Item']

    json_item = dict()
    dynamo_to_json(json_item,db_item)


    channels = json_item['Channels']
    mediapackage = dict()
    region = json_item['Region']

    emp_client = boto3.client('mediapackage',region_name=region)

    db_mediapackage_config_template = mediapackage['M']
    channel_template = db_mediapackage_config_template["1"]["M"]


    # Iterate through channels and create MediaPackage channels

    for channel in range(1,int(channels)+1):

        endpoint_list = []

        channel_name = "{0:0=2d}_{1}_{2}".format(channel,deployment_name,unique_timestamp)

        # Create MediaPackage Channel
        create_emp_response = create_mediapackage_channel(channel_name)

        if len(exceptions) > 0:

            return errorOut()

        LOGGER.info("Created MediaPackage Channel: channel number %s , Channel name %s" % (str(channel),channel_name))

        # Create MediaPackage Channel Endpoints
        endpoints = []
        endpoints.clear()
        create_mediapackage_endpoint(channel_name)

        if len(exceptions) > 0:
            return errorOut()

        # Get response data to variables
        channel_id = create_emp_response['Id']
        channel_arn = create_emp_response['Arn']

        channel_dict = dict()
        channel_dict['Endpoints'] = endpoints
        channel_dict['Channel_Name'] = channel_id
        channel_dict['Channel_Arn'] = channel_arn


        db_mediapackage_config_template[str(channel)] = channel_dict

    if len(exceptions) > 0:
        return errorOut()

    # Update the DB json with the MediaConnect flow information
    db_item['MediaPackage'] = {'M':db_mediapackage_config_template}

    putItem(db_item)
    if len(exceptions) > 0:
        return errorOut()
    else:
        event['status'] = "Completed creation of MediaPackage channels with no issues"
        return event