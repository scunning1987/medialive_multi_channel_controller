'''
Copyright (c) 2021 Scott Cunningham

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Summary: This script is a custom resource to place the HTML pages and Lambda code into the destination bucket.

Original Author: Scott Cunningham
'''

import json
import boto3
import urllib3
from urllib.parse import urlparse
import base64
import os

def lambda_handler(event, context):

    placeholder_bucket = os.environ['PLACEHOLDER_JPG_BUCKET']
    placeholder_key = os.environ['PLACEHOLDER_JPG_KEY']

    # Layout for API Response
    def api_response(status_code,headers,body,base64encoded):
        response_body = {
            "statusCode":status_code,
            "headers":headers,
            "body":body,
            "isBase64Encoded": base64encoded
        }
        return response_body

    ## Log the incoming event
    print("Event : %s " % (event))

    ## Initialize S3 boto3 client
    s3 = boto3.client('s3')

    # Create urllib3 pool manager
    http = urllib3.PoolManager()

    # parse event for bucket and key
    try:
        bucket = event['pathParameters']['proxy'].split("/")[0]
        key =  '/'.join(event['pathParameters']['proxy'].split("/")[1:])
    except:
        body = "request url not well formed"
        base64encoded = False
        return api_response(500,headers,body,base64encoded)

    try:
        s3_response = s3.get_object(Bucket=bucket, Key=key)
        headers = s3_response['ResponseMetadata']['HTTPHeaders']
        if ".jpg" in key:
            body = base64.b64encode(s3_response['Body'].read()).decode('utf-8')
            base64encoded = True
        else:
            body = s3_response['Body'].read().decode('utf-8')
            base64encoded = False
        return api_response(200,headers,body,base64encoded)
    except Exception as e:
        if ".jpg" in key:
            try:
                s3_response = s3.get_object(Bucket=placeholder_bucket, Key=placeholder_key)
                headers = s3_response['ResponseMetadata']['HTTPHeaders']
                body = base64.b64encode(s3_response['Body'].read()).decode('utf-8')
                base64encoded = True
                return api_response(200,headers,body,base64encoded)
            except:
                body = ""
                base64encoded = False
                return api_response(404,headers,body,base64encoded)
        else:

            headers = {"content-type":"application/json"}
            #body = json.dumps(e, default = lambda o: f"<<non-serializable: {type(o).__qualname__}>>")
            body = json.dumps(str(e))
            base64encoded = False
            return api_response(500,headers,body,base64encoded)