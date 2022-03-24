'''
Original Author: Scott Cunningham
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining 
a copy of this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the 
Software, and to permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR 
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE 
FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR 
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
DEALINGS IN THE SOFTWARE.
'''
import json
import boto3
import logging
import os

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

def lambda_handler(event, context):
    LOGGER.info("Event info : %s " % (event))

    region = event['region']

    #eml client
    client = boto3.client('medialive', region_name=region)
    # boto3 S3 initialization
    s3_client = boto3.client("s3")


    event_state = event['detail']['state']
    slate_bucket = os.environ['SLATE_BUCKET']
    slate_key_starting = os.environ['SLATE_KEY_STARTING']
    slate_key_stopping = os.environ['SLATE_KEY_STOPPING']
    slate_key_stopped = os.environ['SLATE_KEY_STOPPED']

    s3_destination = ""

    ## FUNCTION BLOCK START

    def errorOut():
        event['status'] = exceptions
        raise Exception("Unable to complete function : %s" % (event))
        ### NEED TO raise exception here!
        return event

    def describe_channel(channelid):
        LOGGER.info("Getting channel information from channel : %s" % (channelid))
        try:
            response = client.describe_channel(
                ChannelId=channelid
            )
            #print(json.dumps(response))
        except Exception as e:
            msg = "Unable to get channel info, got exception: %s" % (e)
            exceptions.append(msg)
            return msg

        return response['Destinations']

    ## FUNCTION BLOCK END

    exceptions = []
    exceptions.clear()

    try:
        channelid = event['detail']['channel_arn'].split(":")[-1]
        medialive_destinations = describe_channel(channelid)
    except Exception as e:
        msg = "Unable to parse channel arn for channel id, got exception : %s " % (e)
        LOGGER.error(msg)
        exceptions.append(msg)
        errorOut()


    for destination in medialive_destinations:
        if len(destination['Settings']) > 0: ## probably S3 output
            if "s3" in destination['Settings'][0]['Url']:
                LOGGER.info("Found S3 Output in MediaLive Channel destination: %s")
                s3_destination = destination['Settings'][0]['Url']
                LOGGER.info("S3 URL : %s " % (s3_destination))

    if event_state == "STOPPED":
        slate_key = slate_key_stopped
    elif event_state == "IDLE":
        slate_key = slate_key_stopped
    elif event_state == "STOPPING":
        slate_key = slate_key_stopping
    else: # STARTING
        slate_key = slate_key_starting

    LOGGER.info("Event state is : %s , going to use slate jpg %s " % (event_state,slate_key))

    if "s3ssl" in s3_destination:
        bucket_name = s3_destination.replace("s3ssl://","").rsplit("/")[0]
        new_key_name = s3_destination.replace("s3ssl://","").replace(bucket_name+"/","") + ".jpg"
    else:
        bucket_name = s3_destination.replace("s3://","").rsplit("/")[0]
        new_key_name = s3_destination.replace("s3://","").replace(bucket_name+"/","") + ".jpg"

    # Copy Source Object
    copy_source_object = {'Bucket': slate_bucket, 'Key': slate_key}

    try:
        # S3 copy object operation
        response = s3_client.copy_object(CopySource=copy_source_object, Bucket=bucket_name, Key=new_key_name)
    except Exception as e:
        msg = "Unable to replace key in destination, got exception : %s " % (e)
        exceptions.append
        LOGGER.error(msg)
        errorOut()

    return "SUCCESS"