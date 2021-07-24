import json
import os
import boto3
import logging

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
            "body":json.dumps({"status":message})
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
            except:
                LOGGER.error("Unable to get config from S3, please contact support")
                return api_response(500,"Unable to get config from S3, please contact support")
        
        elif event['pathParameters']['proxy'] == "template":
            LOGGER.info("Caller wants template config returned")
            
            # Get object from S3
            try:
                response = s3.get_object(Bucket=bucket,Key=channel_template_key)
                response_str = response['Body'].read()
                return api_response(200,json.loads(response_str))
            except:
                LOGGER.error("Unable to get config from S3, please contact support")
                return api_response(500,"Unable to get config from S3, please contact support")
        
        else: 
            LOGGER.error("Caller has sent unknown get resource path, returning HTTP500.. path sent : %s" % (event['pathParameters']['proxy']))
            return api_response(500,"Caller has sent unknown get resource path, please use 'dashboard-config/existing' or 'dashboard-config/template'")
            
    elif event['httpMethod'] == "PUT":
        LOGGER.info("The API request was a PUT request")
        
        # need to validate the body
        body_json = json.loads(event['body'])
        
        # check length
        if len(body_json) < 1:
            return api_response(500,"malformed api body, please refer to the template")
        
        # check main keys are present
        main_keys = ["channel_map","vod_bucket","channel_start_slate","dashboard_title"]
        for main_key in list(body_json.keys()):
            if main_key not in main_keys:
                return api_response(500,"malformed api body, please refer to the template")
        
        # check channel start slate references mp4
        if ".mp4" not in body_json['channel_start_slate'] or ".MP4" not in body_json['channel_start_slate']:
            return api_response(500,"Channel start slate must reference an MP4 file")
        
        # iterate through channel_map to make sure everything is valid
        
        
        # if validate ok, put to s3
        
        # return 200 to caller
    
    
    else:
        LOGGER.error("Caller has sent unsupported method, returning HTTP500")
        return api_response(500,"Caller has sent unsupported method '%s', use PUT or GET" % (event['httpMethod']))


