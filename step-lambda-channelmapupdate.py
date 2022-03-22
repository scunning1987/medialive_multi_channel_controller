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

#json.loads(json.dumps(response, default = lambda o: f"<<non-serializable: {type(o).__qualname__}>>"))

bucket = os.environ['Bucket']
key = os.environ['Config_Key']

def lambda_handler(event, context):

    dynamodb_table_name= event['detail']['dynamodb_table_name']
    deployment_name = event['detail']['name']
    task = event['detail']['task']

    ###
    ### FUNCTIONS
    ###

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

    def get_channel_map(bucket,key):
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

    region = json_item['Region']

    return json_item
    if task == "create":
        ## Adding deployment info to channel map
        LOGGER.info("Adding group %s from channel map" % (deployment_name))

        channel_map_json = get_channel_map(bucket,key)

        channel_list = []



        deployment_info = dict()
        deployment_info['mux_details'] = {"total_rate":0,"output":"emx_arn"}
        deployment_info['region'] = region
        deployment_info['channels'] = channel_list



        channel_map_json['channel_groups'][deployment_name] = deployment_info

        return channel_map_json


        # "channel_groups": {
        #     "group_name": {
        #       "mux_details": {
        #         "total_rate": 35000000,
        #         "output": "udp://10.10.10.10:12000"
        #       },
        #       "region": "us-west-2",
        #       "channels": [
        #         {
        #           "mux_channel_name": "channel1",
        #           "mux_channel_id": 123456,
        #           "frame_size": "hd/sd",
        #           "codec": "avc/mpeg2",
        #           "ott_channel_id": 123457,
        #           "ott_url": "https://...m3u8",
        #           "jpg_url": "https://...jpg"
        #         }
        #       ]
        #     }
        #   },


    else: ## this is delete
        ## Deletinng deployment info from channel map
        LOGGER.info("Deleting group %s from channel map" % (deployment_name))