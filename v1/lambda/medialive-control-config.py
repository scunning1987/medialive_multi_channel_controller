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
            except Exception as e:
                LOGGER.error("Unable to get config from S3, please contact support - exception : %s " % (e))
                return api_response(500,"Unable to get config from S3, please contact support")

        elif event['pathParameters']['proxy'] == "template":
            LOGGER.info("Caller wants template config returned")

            # Get object from S3
            try:
                response = s3.get_object(Bucket=bucket,Key=channel_template_key)
                response_str = response['Body'].read()
                return api_response(200,json.loads(response_str))
            except Exception as e:
                LOGGER.error("Unable to get config from S3, please contact support - exception : %s " % (e))
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
        if ".mp4" not in str(body_json['channel_start_slate']).lower():
            return api_response(500,"Channel start slate must reference an MP4 file")

        # add check for bucket...

        # add check for deployment title - possibly limit on characters

        # initialize an exceptions list to track any issues with the API submission
        json_exceptions = []
        json_exceptions.clear()

        # iterate through channel_map to make sure everything is valid
        channel_number = 1
        channel_map = body_json['channel_map']
        try:
            for channel in channel_map:
                ## should be an "int" style key that starts from "1", and the value shouold be a list with 6 entries
                if channel_number != int(channel):
                    return api_response(500,"Channel key must look like an integer and start from 1 and increment by 1 for each channel. please refer to the template")

                ## check value list length to be 6
                if isinstance(channel_map[channel],list) == False:
                    if len(channel_map[channel]) != 6:
                        return api_response(500,"Channel key must contain a list value with 6 entries: channelid (int), channel code (str), aws region (str), https jpg url (str), hls url (str), promo videos (list, 4 entries)")

                ## check item 0 is number (this is medialive channnel id)
                if isinstance(channel_map[channel][0],int) == False:
                    return api_response(500,"Channelid must be a valid integer")

                ## check item 1 is a valid string less than 10 characters
                if len(channel_map[channel][1]) > 10:
                    return api_response(500,"Channel code must be less than 10 characters in length")

                ## check item 2 is string (improve this)
                if isinstance(channel_map[channel][2],str) == False:
                    return api_response(500,"Region code doesnt look right")

                ## check item 3 contains jpg in the url
                if ".jpg" not in channel_map[channel][3]:
                    return api_response(500,"Thumbnail URL is invalid or not pointing to a jpg file")

                ## check item 4 contains m3u8 in the url
                if ".m3u8" not in channel_map[channel][4]:
                    return api_response(500,"HLS URL is invalid or not pointing to an HLS index file")

                ## check item 5 is a list with 4 entries
                if isinstance(channel_map[channel][5],list) == False:
                    if len(channel_map[channel][5]) != 4:
                        return api_response(500,"Not submitted the right amount of promo URL's. Should be 4 in list format")

                #### check item 5 list contains valid s3 links to mp4s
                for item in channel_map[channel][5]:
                    if "s3://" not in item.lower() or ".mp4" not in item.lower():
                        return api_response(500,"Promo S3 url is not valid. must be s3:// protocol and reference an MP4 file")

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
            put_response = s3.put_object(Bucket=bucket,Key=channel_config_key,ACL='public-read',CacheControl='no-cache',ContentType='application/json')
            return api_response(200,"New config loaded successfully.")
        except Exception as e:
            return api_response(500,"Unable to publish new config to S3, please try again. If the problem persists, please reach out to support")
    else:
        LOGGER.error("Caller has sent unsupported method, returning HTTP500")
        return api_response(500,"Caller has sent unsupported method '%s', use PUT or GET" % (event['httpMethod']))