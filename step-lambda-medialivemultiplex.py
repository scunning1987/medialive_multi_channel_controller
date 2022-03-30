import json
import boto3
import os
import logging
import datetime
import re
import uuid
import base64
import time

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

unique_timestamp = str(datetime.datetime.now().strftime('%s'))
exceptions = []
role_arn = "arn:aws:iam::301520684698:role/MediaLiveAccessRole" # MediaLive Role

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

    def createMultiplex(az,bitrate,muxid,muxname):
        try:
            eml_create_mux_response = eml_client.create_multiplex(AvailabilityZones=az,MultiplexSettings={"TransportStreamBitrate":bitrate,"TransportStreamId":muxid},Name=muxname)
        except Exception as e:
            msg = "Unable to create multiplex, got exception : %s" % (e)
            LOGGER.error(msg)
            exceptions.append(msg)
            eml_create_mux_response = msg
        LOGGER.info("MediaLive Multiplex Created : %s " % (eml_create_mux_response))
        return eml_create_mux_response

    def createProgram(multiplex_id,program_name,program_id,program_settings):
        try:
            eml_create_prg_response = eml_client.create_multiplex_program(MultiplexId=multiplex_id,ProgramName=program_name,MultiplexProgramSettings=program_settings)
        except Exception as e:
            msg = "Unable to create program in multiplex %s , got exception : %s" % (multiplex_id,e)
            LOGGER.error(msg)
            exceptions.append(msg)
            eml_create_prg_response = msg
        LOGGER.info("MediaLive Multiplex Program Created : %s " % (eml_create_prg_response))
        return eml_create_prg_response

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

    # initialize medialive boto3 client
    eml_client = boto3.client('medialive', region_name=region)

    if task == "create":

        multiplex_db_item = dict()
        mediaconnect_db_item = dict()

        if event['detail']['channel_data']['mux']['create'] == "True":
            LOGGER.info("This deployment requires creation of a multiplex")
            #
            #
            # Create Multiplex
            #
            #

            az = ["%s%s" % (region,"b"), "%s%s" % (region,"c")]
            bitrate = int(event['detail']['channel_data']['mux']['bitrate'])
            muxid = 1
            muxname = event['detail']['channel_data']['mux']['multiplex_name']

            LOGGER.info("Mux creation info: AZs = %s , bitrate = %s , muxid = %s , muxname = %s " % (az,bitrate,muxid,muxname))

            create_mux_response = createMultiplex(az,bitrate,muxid,muxname)

            if len(exceptions) > 0:
                return errorOut()


            multiplex_arn = create_mux_response['Multiplex']['Arn']
            multiplex_id = str(create_mux_response['Multiplex']['Id'])
            multiplex_name = create_mux_response['Multiplex']['Name']

            multiplex_db_item["1"] = {"Multiplex_Name":multiplex_name,"Multiplex_Arn":multiplex_arn,"Multiplex_Id":multiplex_id,"Programs":{}}

            # create programs for each channel in the group
            programs = dict()
            for channel in range(1,int(channels)+1):

                program_name = event['detail']['channel_data']['channels'][channel-1]['program_name'].replace("-","_")
                program_id = event['detail']['channel_data']['channels'][channel-1]['program_number']
                program_settings = {
                    "ProgramNumber":int(program_id),
                    "ServiceDescriptor":{
                        "ProviderName":program_name,
                        "ServiceName":program_name
                    }}

                create_program_response = createProgram(multiplex_id,program_name,program_id,program_settings)

                multiplex_program_settings = create_program_response['MultiplexProgram']['MultiplexProgramSettings']
                multiplex_program_settings['ProgramName'] = create_program_response['MultiplexProgram']['ProgramName']

                if len(exceptions) > 0:
                    return errorOut()

                programs[str(channel)] = multiplex_program_settings

            multiplex_db_item["1"]['Programs'] = programs

            json_item['Multiplex'] = multiplex_db_item

            eml_dict_to_dynamo = dict()
            json_to_dynamo(eml_dict_to_dynamo,json_item)

            putItem(eml_dict_to_dynamo)
            if len(exceptions) > 0:
                return errorOut()
            else:
                event['status'] = "Completed creation of MediaLive Multiplex and Programs with no issues"
                return event

        else:

            LOGGER.info("Task is create, but this is not a mux group, skipping this step")

            event['status'] = "Task is create, but this is not a mux group, skipping this step"
            return event

    else: # we're here to delete

        LOGGER.info("The task is delete, but it will not be handled at this Step")

        event['status'] = "Nothing to do at this step"
        return event