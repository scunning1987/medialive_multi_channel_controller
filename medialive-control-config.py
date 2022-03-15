import json
import os
import boto3
import logging
import base64

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

def lambda_handler(event, context):

    # initialize s3 client
    s3 = boto3.client('s3')

    # environment variables
    bucket = os.environ['BUCKET']
    channel_config_key = os.environ['CONFIG_KEY']
    channel_template_key = os.environ['TEMPLATE_KEY']

    # print incoming event body
    LOGGER.info("incoming data: %s " % (event))


    # Layout for API Response
    def api_response(status_code,message):
        response_body = {
            "statusCode":status_code,
            "headers":{
                "Content-Type":"application/json"
            },
            "body":json.dumps(message)
        }
        return response_body

    # IF GET REQUEST
    if event['httpMethod'] == "GET":
        LOGGER.info("The API request was a GET request")

        if event['pathParameters']['proxy'] == "existing":
            LOGGER.info("Caller wants existing config returned")

            # Get object from S3
            try:
                response = s3.get_object(Bucket=bucket,Key=channel_config_key)
                response_str = response['Body'].read()
                return api_response(200,json.loads(response_str))
            except Exception as e:
                LOGGER.error("Unable to get config from S3, please contact support - exception : %s " % (e))
                return api_response(500,{"status":"Unable to get config from S3, please contact support"})

        elif event['pathParameters']['proxy'] == "template":
            LOGGER.info("Caller wants template config returned")

            # Get object from S3
            try:
                response = s3.get_object(Bucket=bucket,Key=channel_template_key)
                response_str = response['Body'].read()
                return api_response(200,json.loads(response_str))
            except Exception as e:
                LOGGER.error("Unable to get config from S3, please contact support - exception : %s " % (e))
                return api_response(500,{"status":"Unable to get config from S3, please contact support"})

        else:
            LOGGER.error("Caller has sent unknown get resource path, returning HTTP500.. path sent : %s" % (event['pathParameters']['proxy']))
            return api_response(500,{"status":"Caller has sent unknown get resource path, please use 'dashboard-cfg/existing' or 'dashboard-cfg/template'"})

    elif event['httpMethod'] == "PUT":
        LOGGER.info("The API request was a PUT request")

        # need to validate the body
        if event['isBase64Encoded']:
            # Decode body
            body_string =  base64.b64decode(event['body'])
        else:
            body_string = event['body']

        body_json = json.loads(body_string)

        # check length
        if len(body_json) < 1:
            return api_response(500,{"status":"malformed api body, please refer to the template"})

        # check main keys are present
        main_keys = ["channel_map","vod_bucket","dashboard_title","control_api_endpoint_url","bumper_bucket_region","bumper_groups"]
        for main_key in list(body_json.keys()):
            if main_key not in main_keys:
                return api_response(500,{"status":"malformed api body, please refer to the template, missing one of %s " % (main_keys)})

        # check bumper groups dont exceed 5 bumpers per group
        for bumper_group in body_json['bumper_groups']:
            if len(body_json['bumper_groups'][bumper_group]['bumpers']) > 5:
                return api_response(500,"Bumper groups have a limit of 5 bumpers per group")

        # check channel start slate references mp4 ### DEPRECATED FROM UI
        #if ".mp4" not in str(body_json['channel_start_slate']).lower():
        #    return api_response(500,{"status":"Channel start slate must reference an MP4 file"})

        # add check for bucket...

        # add check for deployment title - possibly limit on characters

        # initialize an exceptions list to track any issues with the API submission
        json_exceptions = []
        json_exceptions.clear()

        # iterate through channel_map to make sure everything is valid

        '''
        "channel_map": {
            "1": {
              "primary_channel_id": 4856923,
              "proxy_gen_channel": 123,
              "channel_friendly_name": "MLS Channel 1",
              "channel_region": "us-west-2",
              "low_latency_url_source": "ws://34.212.225.202:8081/emx/20001",
              "low_latency_url_medialive": "ws://34.212.225.202:8081/eml/20001",
            },
        '''


        channel_number = 1
        channel_map = body_json['channel_map']
        try:
            for channel in channel_map:
                ## should be an "int" style key that starts from "1", and the value shouold be a list with 6 entries
                if channel_number != int(channel):
                    return api_response(500,"Channel key must look like an integer and start from 1 and increment by 1 for each channel. please refer to the template")

                ## check channel map is of type dictionary
                if isinstance(channel_map[channel],dict) == False:
                    return api_response(500,{"status":"channel key is not of type dictionary"})

                # Check channel map keys are present
                channel_keys = ["primary_channel_id","proxy_gen_channel","channel_friendly_name","channel_region","low_latency_url_source","low_latency_url_medialive","proxy_thumbnail_name","mediaconnect_ingress_arn","mediaconnect_egress_arn"]
                for channel_key in list(channel_map[channel].keys()):
                    if channel_key not in channel_keys:
                        return api_response(500,{"status":"channel dictionary is missing one or more keys. should contain %s " % (channel_keys)})

                # Add one to the channel index as you iterate through
                channel_number +=1
        except Exception as e:
            return api_response(500,"Unable to process the submitted JSON body. Please validate the json and try again")

        # if validate ok, put to s3
        # # environment variables
        # bucket
        # channel_config_key
        # body = body_json
        # content_type = application/json
        # cache_control = 0
        try:
            s3.put_object(Bucket=bucket,Body=json.dumps(body_json),Key=channel_config_key,CacheControl='no-cache',ContentType='application/json')
            return api_response(200,{"Status":"New config loaded successfully"})
        except Exception as e:
            return api_response(500,{"Status":"Unable to publish new config to S3, please try again. If the problem persists, please reach out to support"})
    else:
        LOGGER.error("Caller has sent unsupported method, returning HTTP500")
        return api_response(500,{"Status":"Caller has sent unsupported method '%s', use PUT or GET"} % (event['httpMethod']))