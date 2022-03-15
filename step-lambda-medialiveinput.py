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
#role_arn = "arn:aws:iam::301520684698:role/MediaLiveAccessRole" # MediaLive Role

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
            key = {'Deployment_Name':{'S':deployment_name}}
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

    def createEMLInput(input_type,input_name,flows):
        if input_type == "MediaConnect":
            try:
                input_name_emx = input_name + "_" + input_type.lower()
                input_create_response = eml_client.create_input(MediaConnectFlows=flows,Type='MEDIACONNECT',Name=input_name_emx,RoleArn=role_arn)
            except Exception as e:
                exceptions.append("Couldn't create input, got exception %s " % (e))
                LOGGER.error("Couldn't create input, got exception %s " % (e))
                return "Couldn't create input, got exception %s " % (e)
            return input_create_response

        else: # Input to create is MP4
            try:
                input_name_mp4 = input_name + "_" + input_type.lower()
                flows = []
                input_create_response = eml_client.create_input(MediaConnectFlows=flows,Type='MP4_FILE',Name=input_name_mp4,Sources=[{'Url':'s3ssl://$urlPath$'}],RoleArn=role_arn)
            except Exception as e:
                exceptions.append("Couldn't create input, got exception %s " % (e))
                LOGGER.error("Couldn't create input, got exception %s " % (e))
                return "Couldn't create input, got exception %s " % (e)
            return input_create_response

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

    ###
    ### FUNCTIONS
    ###

    exceptions.clear()

    # Call DynamoDB to get the deployment information
    db_client = boto3.client('dynamodb')
    try:
        db_item = getItem()['Item']
    except Exception as e:
        LOGGER.error("DB Item doesn't appear to be in DynamoDB table, got exception : %s" % (e))
        raise Exception("DB Item doesn't appear to be in DynamoDB table, got exception : %s" % (e))

    channels = db_item['Channels']['S']
    medialive = db_item['MediaLive']
    region = db_item['Region']['S']
    pipeline = db_item['Pipeline']['S']
    eml_client = boto3.client('medialive', region_name=region)

    db_medialive_config_template = medialive['M']
    channel_template = db_medialive_config_template["1"]["M"]

    loglevel = os.environ['LogLevel']
    role_arn = os.environ['RoleArn']
    max_resolution = os.environ['Input_MaxResolution']
    max_bitrate = os.environ['Input_MaxBitrate']
    input_codec = os.environ['Input_Codec']
    jpg_bucket = os.environ['JPG_Bucket']
    jpg_base_path = os.environ['JPG_KeyPath']

    with open('eml_channel_template.json', 'r') as f:
        eml_template_string = f.read()
    emltemplate = json.loads(eml_template_string)

    # pull some data from the attached channel template
    encoder_settings = emltemplate['EncoderSettings']
    destinations_template = emltemplate['Destinations']

    # Iterate through channels and create MediaConnect flows for each channel

    for channel in range(1,int(channels)+1):

        endpoint_list = []
        input_attachments = []
        dynamo_input_attachments = []
        input_attachments.clear()
        dynamo_input_attachments.clear()

        channel_name = "{0:0=2d}_{1}_{2}".format(channel,deployment_name,unique_timestamp)
        input_name = "{0:0=2d}_{1}".format(channel,deployment_name)

        # Get MediaConnect flow Arns:
        flows = []
        flows.clear()
        for flow in db_item['MediaConnect']['M'][str(channel)]['L']:
            flows.append({'FlowArn':flow['M']['Flow_Arn']['S']})

        # Create MediaLive Inputs
        #
        #  EMX Input
        #  Dynamic MP4 input
        input_types = ["MediaConnect","MP4"]
        input_information = dict()

        for input_type in input_types:
            if input_type == "MP4":
                source_end_behavior = "LOOP"
            else:
                source_end_behavior = "CONTINUE"

            input_create_response = createEMLInput(input_type,input_name,flows)
            if len(exceptions) > 0:
                return errorOut()
            dynamo_input_attachments.append({"S":input_create_response['Input']['Id']})
            input_attachments.append({
                "InputId": input_create_response['Input']['Id'],
                "InputAttachmentName": "%s_%s" % (input_name,input_type.lower()),
                "InputSettings": {
                    "SourceEndBehavior": source_end_behavior,
                    "InputFilter": "AUTO",
                    "FilterStrength": 1,
                    "DeblockFilter": "DISABLED",
                    "DenoiseFilter": "DISABLED",
                    "Smpte2038DataPreference": "IGNORE",
                    "AudioSelectors": [{"Name":"1"}],
                    "CaptionSelectors": []
                }
            })


        LOGGER.info("Created MediaLive Inputs for : channel number %s , Channel name %s" % (str(channel),channel_name))

        # MediaLive Destinations
        emp_channel_id = db_item['MediaPackage']['M'][str(channel)]['M']['Channel_Name']['S']
        jpg_full_path = ""

        for destination in destinations_template:
            if 'MediaPackageSettings' in destination: # This output is to MediaPackage
                LOGGER.debug("This is MediaPackage destination - EMP: %s" % (destination))
                destination['MediaPackageSettings'][0]['ChannelId'] = emp_channel_id # Path to put MediaPackage Channel ID
            elif 'Settings' in destination:
                LOGGER.debug("This is S3 Destination - JPG: %s" % (destination))
                # ottauto/deployments
                jpg_full_path = "s3://%s/%s/%s/%s/status" % (jpg_bucket,jpg_base_path,deployment_name,channel)
                LOGGER.debug("MediaLive Channel %s outputting JPG to %s" % (channel, jpg_full_path))
                destination['Settings'][0]['Url'] = jpg_full_path # Path to s3 published JPG

        # Create Channel
        create_channel_response = createEMLChannel()

        if len(exceptions) > 0:
            return errorOut()

        eml_channel_arn = create_channel_response['Channel']['Arn']

        # update DB Item
        channel_dict = dict()
        channel_dict['MediaPackage_Output'] = {"S":emp_channel_id}
        channel_dict['S3_Output'] = {'S':jpg_full_path}
        channel_dict['Channel_Arn'] = {'S':eml_channel_arn}
        channel_dict['Input_Attachments'] = {"L":dynamo_input_attachments}
        channel_dict['Channel_Name'] = {"S":channel_name}

        db_medialive_config_template[str(channel)] = {"M":channel_dict}


    # Update the DB json with the MediaLive channel information
    db_item['MediaLive'] = {'M':db_medialive_config_template}

    putItem(db_item)
    if len(exceptions) > 0:
        return errorOut()
    else:
        event['status'] = "Completed creation of MediaLive channels with no issues"
        return event