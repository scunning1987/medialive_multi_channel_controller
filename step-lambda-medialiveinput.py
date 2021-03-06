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
role_arn = os.environ['RoleArn'] # MediaLive Role

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

    def createEMLInput(eml_input):

        # {"input_name":"%s-hls-pull-input" % (input_name_prefix),"input_type":"URL_PULL","url":"https://nowhere.com/manifest.m3u8"},
        # {"input_name":"%s-mp4-loop" % (input_name_prefix),"input_type":"MP4","url":"s3ssl://$urlPath$"},
        # {"input_name":"%s-mp4-continue" % (input_name_prefix),"input_type":"MP4","url":"s3ssl://$urlPath$"}
        # {"input_name":"%s-emx" % (input_name_prefix),"input_type":"MEDIACONNECT","arn":""}

        input_name = eml_input['input_name']
        input_type = eml_input['input_type']
        LOGGER.info("Input Type to create : %s " % (input_type))


        if input_type == "MEDIACONNECT":

            flow_arns = eml_input['arn']

            try:
                input_create_response = eml_client.create_input(MediaConnectFlows=[{"FlowArn":flow_arns[0]},{"FlowArn":flow_arns[1]}],Type=input_type,Name=input_name,RoleArn=role_arn)
            except Exception as e:
                exceptions.append("Couldn't create EMX input, got exception %s " % (e))
                LOGGER.error("Couldn't create input, got exception %s " % (e))
                return "Couldn't create input, got exception %s " % (e)
            LOGGER.info("Created MEDIACONNECT input")
            return input_create_response

        elif input_type == "MP4_FILE":

            try:
                input_create_response = eml_client.create_input(Type=input_type,Name=input_name,Sources=[{'Url':eml_input['url']},{'Url':eml_input['url']}],RoleArn=role_arn)
            except Exception as e:
                exceptions.append("Couldn't create MP4 input, got exception %s " % (e))
                LOGGER.error("Couldn't create input, got exception %s " % (e))
                return "Couldn't create input, got exception %s " % (e)
            LOGGER.info("Created MP4 input")
            return input_create_response

        elif input_type == "URL_PULL":

            try:
                input_create_response = eml_client.create_input(Type=input_type,Name=input_name,Sources=[{'Url':eml_input['url']},{'Url':eml_input['url']}],RoleArn=role_arn)
            except Exception as e:
                exceptions.append("Couldn't create PULL input, got exception %s " % (e))
                LOGGER.error("Couldn't create input, got exception %s " % (e))
                return "Couldn't create input, got exception %s " % (e)
            LOGGER.info("Created URL PULL input")
            return input_create_response

    def emlInputCreation(prefix):

        name_prefix = "%s-%s" % (prefix,input_name_prefix)

        eml_input_list = []
        eml_input_list = [
            {"input_name":"%s-emx" % (name_prefix),"input_type":"MEDIACONNECT","arn":emx_flow_arns},
            # {"input_name":"%s-hls-pull-input" % (name_prefix),"input_type":"URL_PULL","url":"https://af93123e0d76e324607b5414578c69b2.p05sqb.channel-assembly.mediatailor.us-west-2.amazonaws.com/v1/channel/cunsco-1/hls.m3u8"},
            {"input_name":"%s-mp4-loop" % (name_prefix),"input_type":"MP4_FILE","url":"s3ssl://$urlPath$"},
            {"input_name":"%s-mp4-continue" % (name_prefix),"input_type":"MP4_FILE","url":"s3ssl://$urlPath$"}
        ]

        for eml_input in eml_input_list:


            LOGGER.info("EML Input dictionary : %s " % (eml_input))
            input_create_response = createEMLInput(eml_input)

            if len(exceptions) > 0:

                return errorOut()

            input_attachments.append(input_create_response['Input'])
        return input_attachments

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

    def deleteEMLInput(input_id):
        try:
            response = eml_client.delete_input(InputId=input_id)
        except Exception as e:
            msg = "Unable to delete input, got exception : %s " % (e)
            delete_exceptions.append(msg)
            return msg
        return response

    def createFlow(flowname,az):
        LOGGER.info("Creating flow for channel")
        try:
            create_flow_response = emx_client.create_flow(Name=flowname,AvailabilityZone=az,Source={'Name': flowname,'Protocol': 'srt-listener','IngestPort':5000,'WhitelistCidr':'0.0.0.0/0'})
        except Exception as e:
            msg = "Unable to create flow %s, got exception : %s" % (flowname,e)
            LOGGER.error(msg)
            exceptions.append(msg)
            create_flow_response = msg
        LOGGER.info("Done Creating MediaConnect Flow : %s " % (flowname))
        return create_flow_response

    def startFlow(flow_arn):
        try:
            start_flow_response = emx_client.start_flow(FlowArn=flow_arn)
        except Exception as e:
            msg = "Unable to start flow %s, got exception : %s" % (flow_arn,e)
            LOGGER.error(msg)
            exceptions.append(msg)
            start_flow_response = msg
        LOGGER.info("MediaConnect Flow Started : %s " % (flow_arn))
        return start_flow_response

    def describeFlow(existing_flow_arn):
        try:
            describe_response = emx_client.describe_flow(FlowArn=existing_flow_arn)
        except Exception as e:
            msg = "Unable to describe existing MediaConnect flow, arn : %s , got exception : %s " % (existing_flow_arn,e)
            LOGGER.error(msg)
            exceptions.append(msg)
            return msg
        return describe_response

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

    # initialize mediaconnect boto3 client
    emx_client = boto3.client('mediaconnect', region_name=region)

    if task == "create":

        medialive_db_item = dict()
        mediaconnect_db_item = dict()

        pipeline = json_item['Pipeline']

        # task = event['detail']['task']
        # channels = event['detail']['channels']
        # channel_data = event['detail']['channel_data']
        # deployment_name = event['detail']['name']
        # dynamodb_table_name


        # MuxHDTemplate	medialive_multi_channel_controller/main/medialive_channel_template_hdavc_smux.json
        # MuxSDTemplate	medialive_multi_channel_controller/main/medialive_channel_template_sdavc_smux.json
        # OttHDTemplate	medialive_multi_channel_controller/main/medialive_channel_template_hd_abr.json
        # OttSDTemplate	medialive_multi_channel_controller/main/medialive_channel_template_sd_abr.json
        # S3Bucket	dishauto12-s3bucket-1t5bgt3x7j1vx

        if isinstance(channel_data,dict):
            # This includes user input data from the UI


            flow_to_start = []

            for channel in range(0,int(channels)):

                input_name_prefix = "%s_%02d" % (deployment_name,channel+1)

                mediaconnect_flows_info = []
                emx_flow_arns = []

                #
                # Create EMX Flow
                #

                chinputs = channel_data['channels'][channel]['input']

                channel += 1

                for chinput in range(0,len(chinputs)):

                    if chinputs[chinput] == "CREATE":

                        flow_suffixes = ["b","c"]

                        suffix = flow_suffixes[chinput]

                        flowname = "%s_%s" % (input_name_prefix,suffix)
                        az = "%s%s" % (region, suffix)
                        emx_response = createFlow(flowname,az)
                        if len(exceptions) > 0:
                            return errorOut()

                        #
                        # Create Item Structure for DB entry
                        #
                        mediaconnect_flow_info = dict()
                        mediaconnect_flow_info = {
                            "Flow_Name":emx_response['Flow']['Name'],
                            "Flow_Arn":emx_response['Flow']['FlowArn'],
                            "IngestIp":emx_response['Flow']['Source']['IngestIp'],
                            "IngestPort":str(emx_response['Flow']['Source']['IngestPort']),
                            "IngestProtocol":emx_response['Flow']['Source']['Transport']['Protocol']
                        }

                        # this is the Arn of the new Flow
                        emx_flow_arn = emx_response['Flow']['FlowArn']
                        flow_to_start.append(emx_flow_arn)

                        #
                        # Start Flow
                        #
                        #startFlow(emx_flow_arn)

                        if len(exceptions) > 0:

                            return errorOut()

                        emx_flow_arns.append(emx_response['Flow']['FlowArn'])
                        mediaconnect_flows_info.append(mediaconnect_flow_info)


                    else:

                        #
                        # Get Info from MediaConnect
                        #
                        existing_flow_arn = chinputs[chinput]

                        # describe flow
                        describe_flow_response = describeFlow(existing_flow_arn)

                        # error out
                        if len(exceptions) > 0:
                            return errorOut()

                        flow_name = describe_flow_response['Flow']['Name']
                        flow_arn = describe_flow_response['Flow']['FlowArn']
                        flow_ingest_ip = ""
                        flow_ingest_port = ""
                        flow_ingest_protocol = ""


                        if 'EntitlementArn' not in list(describe_flow_response['Flow']['Source'].keys()):
                            flow_ingest_ip = describe_flow_response['Flow']['Source']['IngestIp']
                            flow_ingest_port = str(describe_flow_response['Flow']['Source']['IngestPort'])
                            flow_ingest_protocol = describe_flow_response['Flow']['Source']['Transport']['Protocol']
                        else:
                            flow_ingest_ip = describe_flow_response['Flow']['Source']['EntitlementArn']
                            flow_ingest_port = "Entitlement"
                            flow_ingest_protocol = "Entitlement"

                        # add response info to dictionary
                        mediaconnect_flow_info = {
                            "Flow_Name":flow_name,
                            "Flow_Arn":flow_arn,
                            "IngestIp":flow_ingest_ip,
                            "IngestPort":flow_ingest_port,
                            "IngestProtocol":flow_ingest_protocol
                        }

                        mediaconnect_flows_info.append(mediaconnect_flow_info)

                        # This is an ARN for an existing flow, add it to the list of flows in EML input to create
                        emx_flow_arns.append(existing_flow_arn)

                #
                # Create EML Inputs
                #

                input_attachments = []
                emlInputCreation("ott")
                if event['detail']['channel_data']['mux']['create'] == "True":

                    emlInputCreation("mux")

                mediaconnect_db_item[str(channel)] = mediaconnect_flows_info
                medialive_db_item[str(channel)] = {"Input_Attachments":input_attachments}

            json_item['MediaConnect'] = mediaconnect_db_item
            json_item['MediaLive'] = medialive_db_item


        # No data passed in body
        else:

            for channel in range(1,int(channels)+1):

                input_name_prefix = "%s_%02d" % (deployment_name,channel)

                input_attachments = []
                emlInputCreation("ott")
                if event['detail']['channel_data']['mux']['create'] == "True":

                    emlInputCreation("mux")



                medialive_db_item[str(channel)] = {"Input_Attachments":input_attachments}

            json_item['MediaLive'] = medialive_db_item


            # create default inputs
            # 1. Dummy HLS Pull, 2. MP4 dynamic, 3. MP4 Loop

        # channels = db_item['Channels']['S']
        # medialive = db_item['MediaLive']
        # region = db_item['Region']['S']
        # pipeline = db_item['Pipeline']['S']
        # eml_client = boto3.client('medialive', region_name=region)

        # db_medialive_config_template = medialive['M']
        # channel_template = db_medialive_config_template["1"]["M"]

        # loglevel = os.environ['LogLevel']
        # role_arn = os.environ['RoleArn']
        # max_resolution = os.environ['Input_MaxResolution']
        # max_bitrate = os.environ['Input_MaxBitrate']
        # input_codec = os.environ['Input_Codec']
        # jpg_bucket = os.environ['JPG_Bucket']
        # jpg_base_path = os.environ['JPG_KeyPath']

        # with open('eml_channel_template.json', 'r') as f:
        #     eml_template_string = f.read()
        # emltemplate = json.loads(eml_template_string)

        # # pull some data from the attached channel template
        # encoder_settings = emltemplate['EncoderSettings']
        # destinations_template = emltemplate['Destinations']

        # # Iterate through channels and create MediaConnect flows for each channel

        # for channel in range(1,int(channels)+1):

        #     endpoint_list = []
        #     input_attachments = []
        #     dynamo_input_attachments = []
        #     input_attachments.clear()
        #     dynamo_input_attachments.clear()

        #     channel_name = "{0:0=2d}_{1}_{2}".format(channel,deployment_name,unique_timestamp)
        #     input_name = "{0:0=2d}_{1}".format(channel,deployment_name)

        #     # Get MediaConnect flow Arns:
        #     flows = []
        #     flows.clear()
        #     for flow in db_item['MediaConnect']['M'][str(channel)]['L']:
        #         flows.append({'FlowArn':flow['M']['Flow_Arn']['S']})

        #     # Create MediaLive Inputs
        #     #
        #     #  EMX Input
        #     #  Dynamic MP4 input
        #     input_types = ["MediaConnect","MP4"]
        #     input_information = dict()

        #     for input_type in input_types:
        #         if input_type == "MP4":
        #             source_end_behavior = "LOOP"
        #         else:
        #             source_end_behavior = "CONTINUE"

        #         input_create_response = createEMLInput(input_type,input_name,flows)
        #         if len(exceptions) > 0:
        #             return errorOut()
        #         dynamo_input_attachments.append({"S":input_create_response['Input']['Id']})
        #         input_attachments.append({
        #             "InputId": input_create_response['Input']['Id'],
        #             "InputAttachmentName": "%s_%s" % (input_name,input_type.lower()),
        #             "InputSettings": {
        #                 "SourceEndBehavior": source_end_behavior,
        #                 "InputFilter": "AUTO",
        #                 "FilterStrength": 1,
        #                 "DeblockFilter": "DISABLED",
        #                 "DenoiseFilter": "DISABLED",
        #                 "Smpte2038DataPreference": "IGNORE",
        #                 "AudioSelectors": [{"Name":"1"}],
        #                 "CaptionSelectors": []
        #             }
        #         })


        #     LOGGER.info("Created MediaLive Inputs for : channel number %s , Channel name %s" % (str(channel),channel_name))

        #     # MediaLive Destinations
        #     emp_channel_id = db_item['MediaPackage']['M'][str(channel)]['M']['Channel_Name']['S']
        #     jpg_full_path = ""

        #     for destination in destinations_template:
        #         if 'MediaPackageSettings' in destination: # This output is to MediaPackage
        #             LOGGER.debug("This is MediaPackage destination - EMP: %s" % (destination))
        #             destination['MediaPackageSettings'][0]['ChannelId'] = emp_channel_id # Path to put MediaPackage Channel ID
        #         elif 'Settings' in destination:
        #             LOGGER.debug("This is S3 Destination - JPG: %s" % (destination))
        #             # ottauto/deployments
        #             jpg_full_path = "s3://%s/%s/%s/%s/status" % (jpg_bucket,jpg_base_path,deployment_name,channel)
        #             LOGGER.debug("MediaLive Channel %s outputting JPG to %s" % (channel, jpg_full_path))
        #             destination['Settings'][0]['Url'] = jpg_full_path # Path to s3 published JPG

        #     # Create Channel
        #     create_channel_response = createEMLChannel()

        #     if len(exceptions) > 0:
        #         return errorOut()

        #     eml_channel_arn = create_channel_response['Channel']['Arn']

        #     # update DB Item
        #     channel_dict = dict()
        #     channel_dict['MediaPackage_Output'] = {"S":emp_channel_id}
        #     channel_dict['S3_Output'] = {'S':jpg_full_path}
        #     channel_dict['Channel_Arn'] = {'S':eml_channel_arn}
        #     channel_dict['Input_Attachments'] = {"L":dynamo_input_attachments}
        #     channel_dict['Channel_Name'] = {"S":channel_name}

        #     db_medialive_config_template[str(channel)] = {"M":channel_dict}


        # # Update the DB json with the MediaLive channel information
        # db_item['MediaLive'] = {'M':db_medialive_config_template}

        # putItem(db_item)
        # if len(exceptions) > 0:
        #     return errorOut()
        # else:
        #     event['status'] = "Completed creation of MediaLive channels with no issues"
        #     return event


        eml_dict_to_dynamo = dict()
        json_to_dynamo(eml_dict_to_dynamo,json_item)

        putItem(eml_dict_to_dynamo)
        if len(exceptions) > 0:
            return errorOut()
        else:

            LOGGER.info("Flows to start : %s " % (flow_to_start))
            for emx_flow in flow_to_start:
                startFlow(emx_flow)

            event['status'] = "Completed creation of MediaLive inputs with no issues"
            return event


    else: # we're here to delete

        if event['detail']['delete_tasks']['medialive_channels'] == 0:
            event['status'] = "Channels need deleting before inputs. Waiting for Channels to be deleted"
            return event


        time.sleep(10)

        medialive_channels = json_item['MediaLive']
        delete_exceptions = []

        for channel in list(medialive_channels.keys()):

            input_attachments = json_item['MediaLive'][channel]['Input_Attachments']

            for input_attachment in input_attachments:
                input_id = input_attachment['Id']

                ## Send EML Input Delete command
                deleteEMLInput(input_id)

        event['status'] = "Completed deletion of MediaLive Inputs"
        event['detail']['delete_tasks']['medialive_inputs'] = 1
        event['eml_input_delete_exceptions'] = delete_exceptions
        return event