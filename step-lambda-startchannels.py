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


def lambda_handler(event, context):

    task = event['detail']['task']
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
        return response

    def errorOut():
        event['status'] = exceptions
        raise Exception("Unable to complete function : %s" % (event))
        ### NEED TO raise exception here!
        return event


    #########

    def batchStart(channels,multiplexes):
        # start channels
        try:
            response = eml_client.batch_start(ChannelIds=channels,MultiplexIds=multiplexes)
        except Exception as e:
            msg = "Unable to start channels, got exception: %s " % (e)
            exceptions.append(msg)
            LOGGER.error(msg)
            return msg
        return response

    def batchStop(channels,multiplexes):
        # start channels
        try:
            response = eml_client.batch_stop(ChannelIds=channels,MultiplexIds=multiplexes)
        except Exception as e:
            msg = "Unable to start channels, got exception: %s " % (e)
            exceptions.append(msg)
            LOGGER.error(msg)
            return msg
        return response

    def multiplexStart(multiplex_id):
        try:
            response = eml_client.start_multiplex(MultiplexId=multiplex_id)
        except Exception as e:
            msg = "Unable to start multiplex, got exception: %s " % (e)
            exceptions.append(msg)
            LOGGER.error(msg)
            return msg
        return response

    def multiplexStop(multiplex_id):
        try:
            response = eml_client.stop_multiplex(MultiplexId=multiplex_id)
        except Exception as e:
            msg = "Unable to stop multiplex, got exception: %s " % (e)
            exceptions.append(msg)
            LOGGER.error(msg)
            return msg
        return response

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

    # Get list of MediaLive Channels
    channels = []
    for channel_number in json_item['MediaLive']:

        if json_item['MediaLive'][channel_number]['Channel_Arn_OTT'] != "None":
            channel_id = json_item['MediaLive'][channel_number]['Channel_Arn_OTT'].split(":")[-1]
            channels.append(channel_id)
        if json_item['MediaLive'][channel_number]['Channel_Arn_MUX'] != "None":
            channel_id = json_item['MediaLive'][channel_number]['Channel_Arn_MUX'].split(":")[-1]
            channels.append(channel_id)

    if task == "start":
        LOGGER.info("Starting channels for deployment : %s " % (deployment_name))
        state_change_response = batchStart(channels,[])


        if json_item['MediaLive'][channel_number]['Channel_Arn_MUX'] != "None":
            multiplex_id = json_item['Multiplex']['1']['Multiplex_Id']
            state_change_response += multiplexStart(multiplex_id)

        return state_change_response

    else:
        LOGGER.info("Stopping channels for deployment : %s " % (deployment_name))
        response = batchStop(channels,[])

        if json_item['MediaLive'][channel_number]['Channel_Arn_MUX'] != "None":
            multiplex_id = json_item['Multiplex']['1']['Multiplex_Id']
            state_change_response += multiplexStop(multiplex_id)

        return state_change_response
