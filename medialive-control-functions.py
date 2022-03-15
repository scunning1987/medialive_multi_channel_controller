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
import datetime
import time as t
import random
import time
import os
import base64
import urllib3
import math


def lambda_handler(event, context):

    print("INFO : Event Details - ",event)

    event = event['queryStringParameters']

    # global vars:
    # maxresults, channelid, bucket, input/file, awsaccount, follow (actiontofollow), functiontorun

    if ":" in event['channelid']:
        channelid = str(event['channelid'].split(":")[0])
        region = str(event['channelid'].split(":")[1]).split(",")[0]
        station_code = str(event['channelid'].split(":")[0])
    else:
        channelid = str(event['channelid'])
        region = "us-west-2"
        station_code = event['channelid']
    maxresults = int(event['maxresults'])
    awsacc = event['awsaccount']
    input = str(event['input'])
    inputkey = event['input'].replace("%2F","/")
    functiontorun = str(event['functiontorun'])
    follow = str(event['follow'])

    ###
    flow_action = event['functiontorun']
    flow_destination = event['input']
    emxclient = boto3.client('mediaconnect',region_name=region)

    ###

    # initialize dynamodb client
    db_client = boto3.client('dynamodb',region_name=region)


    if ":" in event['bucket']:
        bucket = event['bucket'].split(":")[0]
    else:
        bucket = str(event['bucket'])

    ### Below code will get access & secret key if executing into another account

    if awsacc == "master":
        client = boto3.client('medialive', region_name=region)
        s3 = boto3.resource('s3')
    else:
        sts_connection = boto3.client('sts')
        acct_b = sts_connection.assume_role(
            RoleArn="arn:aws:iam::"+awsacc+":role/AWSLambdaAccessToS3AndEML",
            RoleSessionName="cross_acct_lambda"
        )

        ACCESS_KEY = acct_b['Credentials']['AccessKeyId']
        SECRET_KEY = acct_b['Credentials']['SecretAccessKey']
        SESSION_TOKEN = acct_b['Credentials']['SessionToken']

        client = boto3.client('medialive', region_name=region, aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN,)
        s3 = boto3.resource('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN,)

    # add the below vars inside the batch_update functions
    #   time = datetime.datetime.utcnow()
    #   timestring = time.strftime('%Y-%m-%dT%H%M%SZ')

    ### Function Start : API Response structure ###
    # API template response to API Gateway, for 200 or 500 responses
    def api_response(status_code,message):
        response_body = {
            "statusCode":status_code,
            "headers":{
                "Content-Type":"application/json",
                "Access-Control-Allow-Origin":"*"
            },
            "body":json.dumps(message)
        }
        return response_body
    ### Function End : API Response structure ###

    ### Function Start : list_inputs ###
    def list_inputs(type):
        print("function:list_inputs")
        response = client.list_inputs(MaxResults=maxresults)

        fileinputs = []
        liveinputs = []
        liveinputslist = []
        for channel in response['Inputs']:
            attachedchannelid = str(channel['AttachedChannels'])
            if channelid in attachedchannelid:
                if str(channel['Type']) in ('RTMP_PUSH', 'UDP_PUSH', 'RTP_PUSH', 'RTMP_PULL', 'URL_PULL', 'MEDIACONNECT', 'INPUT_DEVICE') or str(channel['InputSourceType']) == 'STATIC':
                    liveinputs.append({'name' : channel['Name'], 'type' : channel['Type'], 'id':channel['Id']})
                    liveinputslist.append(channel['Name'])
                if "DYNAMIC" in channel['InputSourceType']:
                    fileinputs.append({'name':channel['Name'],'id':channel['Id']})

        if len(fileinputs) is 0:
            print("ERROR: No dynamic inputs attached to this channel!")
        if len(liveinputs) is 0:
            print("ERROR: No live inputs attached to this channel!")

        inputdict = dict()
        inputdict['file'] = fileinputs
        inputdict['live'] = liveinputs
        inputdict['livelist'] = liveinputslist
        if type == "livedashboard": # call originated from dashboard , must return response in json list only
            return liveinputs
        else: # dictionary return
            return inputdict

    ### Function End : list_inputs ###

    ### Function Start : describe_channel ###
    def describe_channel():
        try:
            response = client.describe_channel(
                ChannelId=channelid
            )
            #print(json.dumps(response))
        except Exception as e:
            print(e)
        #current_active = response['PipelineDetails'][0]['ActiveInputSwitchActionName']
        #return current_active
        return response

    ### Function End : describe_channel ###

    ### Function Start : describe_schedule ###

    def describe_schedule(inputs, currentaction, follow):
        response = client.describe_schedule(ChannelId=channelid,MaxResults=maxresults)
        # getting list to reschedule
        schedule = []
        actionpaths = []
        dashboardlist = []
        scheduledic = dict()

        if currentaction == "Initial Channel Input":
            dashboardlist.append({'actionname' : 'Initial Channel Input', 'actionrefname' : 'Initial Channel Input'})

            scheduledic['dashboardlist'] = dashboardlist
            scheduledic['itemstoreschedule'] = []
            scheduledic['itemstodelete'] = []
            return scheduledic

        for action in response['ScheduleActions']:
            if "InputSwitchSettings" in action['ScheduleActionSettings']: # This filters out the input switch actions only
                schedule.append(action['ActionName'])
                if str(action['ScheduleActionSettings']['InputSwitchSettings']['InputAttachmentNameReference']) in inputs['file']:
                    actionpaths.append(action['ScheduleActionSettings']['InputSwitchSettings']['UrlPath'][0])
                    dashboardlist.append({'actionname' : action['ActionName'], 'actionrefname' : action['ScheduleActionSettings']['InputSwitchSettings']['InputAttachmentNameReference']})
                elif str(action['ScheduleActionSettings']['InputSwitchSettings']['InputAttachmentNameReference']) in str(inputs['live']):
                    actionpaths.append(action['ScheduleActionSettings']['InputSwitchSettings']['InputAttachmentNameReference'])
                    dashboardlist.append({'actionname' : action['ActionName'], 'actionrefname' : action['ScheduleActionSettings']['InputSwitchSettings']['InputAttachmentNameReference']})

        scheduledic['lastaction'] = schedule[-1]

        if currentaction == "followlast":
            return scheduledic
        else:

            itemstoreschedule = []
            itemstodelete = []
            dashboardlistsub = []

            if len(schedule) == 0:
                itemstoreschedule = []
            else:
                if follow == "true":
                    indexofactive = schedule.index(currentaction) + 1
                    listlength = len(schedule) + 1
                else:
                    indexofactive = schedule.index(currentaction)
                    listlength = len(schedule)
                # CREATE SUB ARRAY FOR ACTIONS TO REPOPULATE
                itemstoreschedule = actionpaths[indexofactive:listlength]
                itemstodelete = schedule[indexofactive:listlength]
                dashboardlistsub = dashboardlist[indexofactive:listlength]

            scheduledic['itemstoreschedule'] = itemstoreschedule
            scheduledic['itemstodelete'] = itemstodelete
            scheduledic['dashboardlist'] = dashboardlistsub
            return scheduledic

    ### Function End : describe_schedule ###

    ### Function Start : batch_update ###
    def batch_update(type, followaction, inputs, inputfile,input_attachments):
        # types ; immediate, follow, live
        # vars
        time = datetime.datetime.utcnow()
        timestring = time.strftime('%Y-%m-%dT%H%M%SZ')
        actionname = inputfile.rsplit('/', 1)[-1][0:30] + "_" + str(random.randint(100,999)) + "_" + timestring
        inputurl = bucket + "/" + str(inputfile)
        print("action type is : %s " %(type))
        if type == "immediate-continue" or type == "input-prepare":
            # Find a CONTINUE dynamic file (For promo / play once functionality)
            for input in input_attachments:
                if input['InputSettings']['SourceEndBehavior'] == "CONTINUE":
                    for fileinput in inputs['file']:
                        if input['InputId'] == fileinput['id']:
                            inputattachref = input['InputAttachmentName']


        elif type == "live" or "follow-live":

            live_input_id = ""

            for liveinput in inputs['live']:
                if liveinput['name'] == inputfile:
                    live_input_id = liveinput['id']

            for input in input_attachments:
                if input['InputId'] == live_input_id:
                    inputattachref = input['InputAttachmentName']

        if type == "immediate":
            # Find a LOOP attached dynamic file (For Slate loop functionality)

            for input in input_attachments:
                if input['InputSettings']['SourceEndBehavior'] == "LOOP":
                    for fileinput in inputs['file']:
                        if input['InputId'] == fileinput['id']:
                            inputattachref = input['InputAttachmentName']

        if type == "immediate" or type == "immediate-continue":

            try:
                response = client.batch_update_schedule(
                    ChannelId=channelid,
                    Creates={
                        'ScheduleActions': [
                            {
                                'ActionName': actionname,
                                'ScheduleActionSettings': {
                                    'InputSwitchSettings': {
                                        'InputAttachmentNameReference': inputattachref,
                                        'UrlPath': [
                                            inputurl #,inputurl
                                        ]
                                    },
                                },
                                'ScheduleActionStartSettings': {
                                    'ImmediateModeScheduleActionStartSettings': {}

                                }
                            },
                        ]
                    }
                )
                print(json.dumps(response))
            except Exception as e:
                print("Error creating Schedule Action")
                print(e)
            return response

        elif type == "follow":
            response = client.batch_update_schedule(
                ChannelId=channelid,
                Creates={
                    'ScheduleActions': [
                        {
                            'ActionName': actionname,
                            'ScheduleActionSettings': {
                                'InputSwitchSettings': {
                                    'InputAttachmentNameReference': inputattachref,
                                    'UrlPath': [
                                        inputurl #,inputurl
                                    ]
                                },
                            },
                            'ScheduleActionStartSettings': {
                                'FollowModeScheduleActionStartSettings': {
                                    'FollowPoint': 'END',
                                    'ReferenceActionName': followaction
                                },

                            }
                        },
                    ]
                }
            )
            return response

        elif type == "follow-live":
            response = client.batch_update_schedule(
                ChannelId=channelid,
                Creates={
                    'ScheduleActions': [
                        {
                            'ActionName': actionname,
                            'ScheduleActionSettings': {
                                'InputSwitchSettings': {
                                    'InputAttachmentNameReference': inputattachref
                                },
                            },
                            'ScheduleActionStartSettings': {
                                'FollowModeScheduleActionStartSettings': {
                                    'FollowPoint': 'END',
                                    'ReferenceActionName': followaction
                                },

                            }
                        },
                    ]
                }
            )
            return response

        elif type == "input-prepare":
            try:
                response = client.batch_update_schedule(
                    ChannelId=channelid,
                    Creates={
                        'ScheduleActions': [
                            {
                                'ActionName': actionname,
                                'ScheduleActionSettings': {
                                    'InputPrepareSettings': {
                                        'InputAttachmentNameReference': inputattachref,
                                        'UrlPath': [
                                            inputurl #,inputurl
                                        ]
                                    },
                                },
                                'ScheduleActionStartSettings': {
                                    'ImmediateModeScheduleActionStartSettings': {}

                                }
                            },
                        ]
                    }
                )
                print(json.dumps(response))
            except Exception as e:
                print("Error creating Schedule Action")
                print(e)
            return response


        else: # this assumes the type is now LIVE immediate
            try:
                response = client.batch_update_schedule(
                    ChannelId=channelid,
                    Creates={
                        'ScheduleActions': [
                            {
                                'ActionName': actionname,
                                'ScheduleActionSettings': {
                                    'InputSwitchSettings': {
                                        'InputAttachmentNameReference': inputattachref
                                    },
                                },
                                'ScheduleActionStartSettings': {
                                    'ImmediateModeScheduleActionStartSettings': {}
                                }
                            },
                        ]
                    }
                )
                print(json.dumps(response))
            except Exception as e:
                print("Error creating Schedule Action")
                print(e)
            return response

    ### Function End : batch_update ###

    ### Function Start : batch_udpate delete ###
    def batch_update_delete(itemstodelete):
        deletedict = dict()
        deletedict["ActionNames"] = itemstodelete

        # DELETE Items in subarray
        #actionstodelete = ' , '.join('"' + action + '"' for action in actions[0:deleteindex])
        #return actionstodelete
        try:
            response = client.batch_update_schedule(ChannelId=channelid,Deletes=deletedict)
        except Exception as e:
            return e
    ### Function End : batch_udpate delete ###

    ### Function Start : SCTE35 inject ###

    def scteInject():
        event_id = 1001 #id of your choice
        duration = int(event['duration']) * 90000 #duration of ad (10 sec* 90000 Hz ticks)
        time = datetime.datetime.utcnow()
        timestring = time.strftime('%Y-%m-%dT%H%M%SZ')
        actionname = "SCTE35_duration_" + str(event['duration']) + "_seconds_" + timestring
        try:
            response = client.batch_update_schedule(
                ChannelId=channelid,
                Creates={
                    'ScheduleActions':[
                        {
                            'ActionName': actionname,
                            'ScheduleActionSettings': {
                                'Scte35SpliceInsertSettings': {
                                    'SpliceEventId': event_id,
                                    'Duration': duration
                                }
                            },
                            'ScheduleActionStartSettings': {
                                'ImmediateModeScheduleActionStartSettings': {}
                            }
                        }
                    ]
                }
            )
        except Exception as e:
            print("Error creating Schedule Action")
            print(e)
        return response

    ### Function End : SCTE35 inject ###

    #response = client.list_inputs(MaxResults=maxresults)
    #liveinputs = []
    #for channel in response['Inputs']:
    #        attachedchannelid = str(channel['AttachedChannels'])
    #        if channelid in attachedchannelid:
    #            liveinputs.append(channel)
    #return liveinputs


    def immediateSwitch():
        inputs = list_inputs("dictionary") # return dictionary : file, live, livelist
        channel_info = describe_channel()
        #currentaction = channel_info['PipelineDetails'][0]['ActiveInputSwitchActionName'] # return string of current running action
        #itemstoreplace = describe_schedule(inputs, currentaction, "true") # return dictionary : *itemstoreschedule*, itemstodelete, dashboardlist, lastaction
        channel_input_attachments = channel_info['InputAttachments']

        response = batch_update("immediate", "", inputs, inputkey,channel_input_attachments)

        '''
        for item in itemstoreplace['itemstoreschedule']:
            lastaction = describe_schedule(inputs, currentaction, "false") # return dictionary : itemstoreschedule, itemstodelete, dashboardlist, *lastaction*
            batch_update("follow", lastaction['lastaction'], inputs, item,channel_input_attachments)
        return itemstoreplace
        '''
        return response

    def inputPrepare():
        inputs = list_inputs("dictionary") # return dictionary : file, live, livelist
        channel_info = describe_channel()
        channel_input_attachments = channel_info['InputAttachments']
        response = batch_update("input-prepare", "", inputs, inputkey,channel_input_attachments)
        return response

    def immediateSwitchLive():
        inputs = list_inputs("dictionary") # return dictionary : file, live, livelist
        channel_info = describe_channel()
        channel_input_attachments = channel_info['InputAttachments']

        # get the live input to switch to
        for live_input in inputs['live']:
            if live_input['type'] != "MP4_FILE": # We don't want to go back to a static file, rather a LIVE input, this assumes only a single live input is attached
                inputkey = live_input['name']

        return batch_update("live", "", inputs, inputkey, channel_input_attachments)

    def getSchedule():
        inputs = list_inputs("dictionary") # return dictionary : file, live, livelist
        currentaction = describe_channel()['PipelineDetails'][0]['ActiveInputSwitchActionName'] # return string of current running action
        schedule = describe_schedule(inputs, currentaction, "false") # return dictionary : itemstoreschedule, itemstodelete, *dashboardlist*, lastaction
        return schedule['dashboardlist']

    def immediateContinue():
        inputs = list_inputs("dictionary") # return dictionary : file, live, livelist
        channel_info = describe_channel()
        channel_input_attachments = channel_info['InputAttachments']

        # immediate injection of the file to play once
        slate_response = batch_update("immediate-continue", "", inputs, input,channel_input_attachments)

        # follow last
        lastaction = describe_schedule(inputs, "followlast", "true") #

        # get the live input to switch to
        for live_input in inputs['live']:
            if live_input['type'] != "MP4_FILE": # We don't want to go back to a static file, rather a LIVE input, this assumes only a single live input is attached
                inputkey = live_input['name']

        response = batch_update("follow-live", lastaction['lastaction'], inputs, inputkey,channel_input_attachments)
        return response

    def followLast():
        inputs = list_inputs("dictionary") # return dictionary : file, live, livelist
        lastaction = describe_schedule(inputs, "followlast", "true") # return dictionary : itemstoreschedule, itemstodelete, *dashboardlist*, lastaction
        channel_info = describe_channel()
        channel_input_attachments = channel_info['InputAttachments']

        response = batch_update("follow", lastaction['lastaction'], inputs, inputkey,channel_input_attachments)
        return response

    def followCustom():
        inputs = list_inputs("dictionary") # return dictionary : file, live, livelist
        itemstoreplace = describe_schedule(inputs, follow, "true") # return dictionary : itemstoreschedule, itemstodelete, *dashboardlist*, lastaction
        channel_info = describe_channel()
        channel_input_attachments = channel_info['InputAttachments']
        batch_update_delete(itemstoreplace['itemstodelete'])
        batch_update("follow", follow, inputs, inputkey,channel_input_attachments)
        for item in itemstoreplace['itemstoreschedule']:
            lastaction = describe_schedule(inputs, "followlast", "false") # return dictionary : itemstoreschedule, itemstodelete, dashboardlist, *lastaction*
            batch_update("follow", lastaction['lastaction'], inputs, item,channel_input_attachments)
        return itemstoreplace

    def followCurrent():
        inputs = list_inputs("dictionary") # return dictionary : *file*, live, livelist
        channel_info = describe_channel()
        currentaction = channel_info['PipelineDetails'][0]['ActiveInputSwitchActionName'] # return string of current running action
        channel_input_attachments = channel_info['InputAttachments']
        itemstoreplace = describe_schedule(inputs, currentaction, "true") # return dictionary : *itemstoreschedule*, itemstodelete, dashboardlist, lastaction
        batch_update_delete(itemstoreplace['itemstodelete'])
        batch_update("follow", currentaction, inputs, inputkey,channel_input_attachments)
        for item in itemstoreplace['itemstoreschedule']:
            lastaction = describe_schedule(inputs, "followlast", "false") # return dictionary : itemstoreschedule, itemstodelete, dashboardlist, *lastaction*
            batch_update("follow", lastaction['lastaction'], inputs, item,channel_input_attachments)
        return itemstoreplace

    def getLiveInputs():
        inputs = list_inputs("dictionary") # return dictionary : file, live, *livelist*
        ## TESTING ##
        return inputs['live']

    def s3GetAssetList():
        assets = dict() # dictionary
        assets = [] # array/list
        bucket = event['bucket']

        bucket = s3.Bucket(bucket)
        for obj in bucket.objects.all():
            if ".mp4" in str(obj.key):
                #assets.update({'name' : obj.size})
                #assets.append(obj.key)
                assets.append({'name' : obj.key.rsplit('/', 1)[-1], 'size' : obj.size, 'key' : obj.key})
                #assets.append(obj.key)
        return(assets)

    def channelStartStop():
        ## Check channel status
        ## If status is not what the desired action is, perform the action
        channel_summary = client.describe_channel(ChannelId=channelid)
        channel_input_attachments = channel_summary['InputAttachments']
        channel_status = channel_summary['State']

        if input == "start":
            if channel_status != "RUNNING":

                '''
                try:
                # schedule immediate swith to slate:
                slate_path = event['bucket'].split(":")[1].replace("%2F","/")
                inputs = list_inputs("dictionary") # return dictionary : file, live, livelist


                    batch_update("immediate", "", inputs, slate_path,channel_input_attachments)
                except:
                    return "Couldnt change input to slate"
                '''
                ## start api
                try:
                    response = client.start_channel(ChannelId=channelid)
                    return response
                except Exception as e:
                    return e
            else:
                return "Channel is already Running"

        else: # input is stop
            if channel_status == "IDLE" or channel_status == "STOPPING":
                return "Channel already stopping or stopped"
            else:
                # stop api
                try:
                    response = client.stop_channel(ChannelId=channelid)
                    return response
                except Exception as e:
                    return e

    def channelState():
        channellist = []
        if "," in event['channelid']:
            channellist = event['channelid'].split(",")
        else:
            channellist = event['channelid']

        cwatchregions = dict()
        for channel in channellist:

            if ":" in channel:
                channelid = channel.split(":")[0]
                region = channel.split(":")[1].split(",")[0]
            else:
                channelid = channel
                region = "us-west-2" # as a default region to use...

            if region in cwatchregions:
                cwatchregions[region].append(channelid)
            else:
                cwatchregions[region] = []
                cwatchregions[region].append(channelid)


        channelalertlist = []
        #return cwatchregions
        for region in cwatchregions:
            metricstructure = []
            metric_data_queries = []
            del metricstructure[:]
            del metric_data_queries[:]

            # channel id list = cwatchregions[region]
            # region = region
            for channelid in cwatchregions[region]:
                metric_id = "ch_"+channelid
                metric_period = 30
                metric_stat = "Maximum"

                date_now = datetime.datetime.now()
                date_past = datetime.datetime.now() - datetime.timedelta(hours=0, minutes=1, seconds=0)

                #date_past="2020-10-19T21:37:55.315Z"
                #date_now="2020-10-19T21:38:05.315Z"

                # build the metric structure for each channel and append to the metric_data_queries list
                metricstructure = {'Id':metric_id,'MetricStat':{'Metric': {'Namespace': 'MediaLive','MetricName': 'ActiveAlerts','Dimensions': [{'Name': 'ChannelId','Value': channelid},{'Name': 'Pipeline','Value': '0'}]},'Period': metric_period,'Stat': metric_stat}}
                metric_data_queries.append(metricstructure)

            #return metric_data_queries

            client = boto3.client('cloudwatch',region_name=region)
            response = client.get_metric_data(MetricDataQueries=metric_data_queries,StartTime=date_past,EndTime=date_now,MaxDatapoints=100)
            #return str(response)
            for channelmetric in response['MetricDataResults']:

                channelid = channelmetric['Id'].split("_")[1]
                if len(channelmetric['Timestamps']) > 0:
                    if channelmetric['Values'][0] > 0:
                        alertstatus = "true"
                    else:
                        alertstatus = "false"
                else:
                    alertstatus = "false"
                channelalertlist.append({'channel':channelid,'status':alertstatus})
                print("INFO: ChannelId - %s, ActiveAlerts - %s" % (channelid,alertstatus))


        return channelalertlist

    def describeChannelState():
        channel_info = describe_channel()
        try:
            state = {"status":channel_info['State']}
            return state
        except:
            state = {"status":"UNKNOWN"}
            return state

    def presignGenerator():
        # initialize s3 client
        s3_client = boto3.client('s3')

        #bucket = "cunsco-east" # K.wendt mod
        key = input #"INTRO.mp4" # K.wendt mod
        expiration = 180

        try:
            response = s3_client.generate_presigned_url('get_object',Params={'Bucket': bucket,'Key': key},ExpiresIn=expiration)
            return {"url":response}
        except Exception as e:
            return e
            return {"url":"error"}

    def gfxActivate():
        # Vars we need...
        # image HTTPS url

        # Parse vars received in API call
        gfx_settings_list = event['duration'].split(",") # x + "," + y + "," + gfx_duration + "," + gfx_fade
        gfx_x = gfx_settings_list[0]
        gfx_y = gfx_settings_list[1]
        gfx_duration = int(gfx_settings_list[2]) * 1000
        gfx_fade = gfx_settings_list[3]
        gfx_url = "https://%s" % (input)
        layer = 0 # always layer 0 right now

        #generate random action name
        time = datetime.datetime.utcnow()
        timestring = time.strftime('%Y-%m-%dT%H%M%SZ')
        actionname = functiontorun + "_" + str(random.randint(100,999)) + "_" + timestring

        # create schedule actions list for batch submission
        schedule_actions = []

        if input == "":
            # deactivate first.
            schedule_action_deactivate = dict()
            schedule_action_deactivate['ActionName'] = actionname + "_0"
            schedule_action_deactivate['ScheduleActionStartSettings'] = {}
            schedule_action_deactivate['ScheduleActionStartSettings']['ImmediateModeScheduleActionStartSettings'] = {}
            schedule_action_deactivate['ScheduleActionSettings'] = {}
            schedule_action_deactivate['ScheduleActionSettings']['StaticImageDeactivateSettings'] = {}
            schedule_action_deactivate['ScheduleActionSettings']['StaticImageDeactivateSettings']['FadeOut'] = int(gfx_fade)
            schedule_action_deactivate['ScheduleActionSettings']['StaticImageDeactivateSettings']['Layer'] = int(layer)

            schedule_actions.append(schedule_action_deactivate)


            # make the API call to MediaLive
            response = client.batch_update_schedule(ChannelId=channelid,Creates={'ScheduleActions':schedule_actions})

        else:

            schedule_action_activate = dict()
            schedule_action_activate['ActionName'] = actionname + "_1"
            schedule_action_activate['ScheduleActionStartSettings'] = {}
            schedule_action_activate['ScheduleActionStartSettings']['ImmediateModeScheduleActionStartSettings'] = {}
            schedule_action_activate['ScheduleActionSettings'] = {}
            schedule_action_activate['ScheduleActionSettings']['StaticImageActivateSettings'] = {}
            schedule_action_activate['ScheduleActionSettings']['StaticImageActivateSettings']['Duration'] = int(gfx_duration)
            schedule_action_activate['ScheduleActionSettings']['StaticImageActivateSettings']['FadeOut'] = int(gfx_fade)
            schedule_action_activate['ScheduleActionSettings']['StaticImageActivateSettings']['FadeIn'] = int(gfx_fade)
            schedule_action_activate['ScheduleActionSettings']['StaticImageActivateSettings']['Layer'] = int(layer)
            schedule_action_activate['ScheduleActionSettings']['StaticImageActivateSettings']['ImageX'] = int(gfx_x)
            schedule_action_activate['ScheduleActionSettings']['StaticImageActivateSettings']['ImageY'] = int(gfx_y)
            schedule_action_activate['ScheduleActionSettings']['StaticImageActivateSettings']['Width'] = 480
            schedule_action_activate['ScheduleActionSettings']['StaticImageActivateSettings']['Height'] = 260
            schedule_action_activate['ScheduleActionSettings']['StaticImageActivateSettings']['Image'] = {}
            schedule_action_activate['ScheduleActionSettings']['StaticImageActivateSettings']['Image']['Uri'] = gfx_url

            schedule_actions.append(schedule_action_activate)

            # make the API call to MediaLive
            response = client.batch_update_schedule(ChannelId=channelid,Creates={'ScheduleActions':schedule_actions})

        return response

    def channelReservation():

        template_response = dict()
        template_response["1"] = {"reservation_end_time":"0","reservation_name":"na"}
        template_response["2"] = {"reservation_end_time":"0","reservation_name":"na"}
        template_response["3"] = {"reservation_end_time":"0","reservation_name":"na"}
        template_response["4"] = {"reservation_end_time":"0","reservation_name":"na"}

        if input == "reservationsCheck":

            # get all items from Dynamo
            # iterate through
            # respond

            # Function to get DB Item that needs playing

            response = db_client.scan(TableName='ChannelReservation',Limit=10)

            items = response['Items']

            for channel in channelid.split(','):

                try:
                    for item in items:
                        if channel == item['channel']['S']:
                            time = item['reservation_end_time']['S']
                            name = item['reservation_name']['S']
                            template_response[channel] = {"reservation_end_time":time,"reservation_name":name}
                except Exception as e:
                    template_response[channel] = {"reservation_end_time":"0","reservation_name":"NA"}

            return template_response

        else: # this is a reservation attempt
            # awsaccount=master&functiontorun=channelReservation&channelid=2&maxresults=200&bucket=scott&input=makeReservation&follow=300
            reserve_status = dict()

            channel_number = channelid
            reservation_name = bucket
            reservation_end_time = int(follow)
            # need to see if the item exists first, and see if a reservation is currently under way
            # update db item or respond back to api call with issue on reservation

            try:
                get_item_response = db_client.get_item(TableName='ChannelReservation',Key={"channel":{"S":channel_number}})

                if "Item" in get_item_response:
                    reserve_status['herecheck'] = get_item_response['Item']['reservation_end_time']['S']
                    nowtime = datetime.datetime.utcnow()
                    nowtimeepoch = int(nowtime.strftime('%s'))

                    if int(get_item_response['Item']['reservation_end_time']['S']) < nowtimeepoch:
                        reserve_now = True
                    else:
                        reserve_now = False
                        reserve_status['status'] = "FAILED"
                        reserve_status['message'] = "Channel already reserved, please try again later"
                        reserve_status[channel_number] = {}
                        reserve_status[channel_number]['reservation_end_time'] = get_item_response['Item']['reservation_end_time']['S']
                        reserve_status[channel_number]['reservation_name'] = get_item_response['Item']['reservation_name']['S']

                else:
                    # item not created yet.
                    reserve_now = True

                if reserve_now:

                    item_body = {
                        "channel": {
                            "S": channel_number
                        },
                        "reservation_end_time": {
                            "S": str(reservation_end_time)
                        },
                        "reservation_name": {
                            "S": reservation_name
                        }
                    }
                    reserve_status['detail2'] = item_body
                    # put updated item with new end time and alias
                    put_item_response = db_client.put_item(TableName='ChannelReservation',Item=item_body)
                    reserve_status['status'] = "SUCCESS"
                    reserve_status['message'] = "Channel reserved successfully"
                    reserve_status[channel_number] = {}
                    reserve_status[channel_number]['reservation_end_time'] = str(reservation_end_time)
                    reserve_status[channel_number]['reservation_name'] = reservation_name
            except Exception as e:
                reserve_status['status'] = "FAILED"
                reserve_status['message'] = "Something went wrong when reserving the channel. Please try again later"
                reserve_status['detail'] = str(e)
            return reserve_status

    def html5Activate():

        # this function activates the html5 graphics page for a set duration, then sends an API call to the html5 endpoint to clear all graphics off, ready for demo

        #generate random action name
        time = datetime.datetime.utcnow()
        timestring = time.strftime('%Y-%m-%dT%H%M%SZ')
        actionname = functiontorun + "_" + str(random.randint(100,999)) + "_" + timestring

        html5_activate_json = json.loads(base64.b64decode(input))
        duration = int(html5_activate_json['duration'])
        url = html5_activate_json['url']
        html5_endpoint = html5_activate_json['html5_apiendpoint_ctrl']

        # create schedule actions list for batch submission
        schedule_actions = []

        schedule_action_activate = dict()
        schedule_action_activate['ActionName'] = actionname + "_1"
        schedule_action_activate['ScheduleActionStartSettings'] = {}
        schedule_action_activate['ScheduleActionStartSettings']['ImmediateModeScheduleActionStartSettings'] = {}
        schedule_action_activate['ScheduleActionSettings'] = {}
        schedule_action_activate['ScheduleActionSettings']['MotionGraphicsImageActivateSettings'] = {}
        schedule_action_activate['ScheduleActionSettings']['MotionGraphicsImageActivateSettings']['Duration'] = duration
        schedule_action_activate['ScheduleActionSettings']['MotionGraphicsImageActivateSettings']['Url'] = url

        schedule_actions.append(schedule_action_activate)

        # make the API call to MediaLive
        response = client.batch_update_schedule(ChannelId=channelid,Creates={'ScheduleActions':schedule_actions})

        # Clear HTML5 compositions
        # Create urllib3 pool manager
        http = urllib3.PoolManager()

        # Get the html5 appinstance compositions
        get_response = http.request('GET', html5_endpoint)

        if get_response.status != 200:
            # Exit the script with errors
            return "Unable to get file from location : %s " % (html5_endpoint)
        else:
            # Continue and upload to S3
            compositions = json.loads(get_response.data)

        # "Baseline - Crawl" "Score Bug - Soccer" "Lower - 2 Line" "Bug - Social"
        new_compositions = []
        for i in range(0,len(compositions)):
            composition = compositions[i]
            if composition['compositionName'] == "Baseline - Crawl":
                # we are deactivating overlay
                del composition['animation']['state']
                composition['animation']['action'] = "play"
                composition['animation']['to'] = "Out1"
                composition['controlNode']['payload']['Ticker Text'] = " ~ "

                new_compositions.append(composition)
            elif composition['compositionName'] == "Score Bug - Soccer":
                # we are deactivating overlay
                del composition['animation']['state']
                composition['animation']['action'] = "play"
                composition['animation']['to'] = "Out1"
                new_compositions.append(composition)
            elif composition['compositionName'] == "Lower - 2 Line":
                # we are deactivating overlay
                del composition['animation']['state']
                composition['animation']['action'] = "play"
                composition['animation']['to'] = "Out1"
                new_compositions.append(composition)
            elif composition['compositionName'] == "Bug - Social":
                # we are deactivating overlay
                del composition['animation']['state']
                composition['animation']['action'] = "play"
                composition['animation']['to'] = "Out1"
                new_compositions.append(composition)

        new_compositions = json.dumps(new_compositions)

        # Update the html5 render via API
        put_response = http.request('PUT', html5_endpoint,body=new_compositions,headers={"Content-Type": "application/json"})

        return {
            "medialive_response":response,
            "html5_ctrl_response":put_response.status
        }
        #
        # ADD LATER : API CALL TO HTML5 ENDPOINT TO CLEAR GRAPHICS
        #

    def html5Graphics():

        response_status = dict()

        # Create urllib3 pool manager
        http = urllib3.PoolManager()

        html5_json = json.loads(base64.b64decode(input))

        type = html5_json['type'] # html5 graphics type
        onoff = html5_json['onoff'] # activate / deactivate
        html5_endpoint = html5_json['html5_endpoint']

        # Get the html5 appinstance compositions
        get_response = http.request('GET', html5_endpoint)

        if get_response.status != 200:
            # Exit the script with errors
            return "Unable to get file from location : %s " % (html5_endpoint)
        else:
            # Continue and upload to S3
            compositions = json.loads(get_response.data)

        inout = ""
        if onoff == "activate":
            inout = "In"
        else:
            inout = "Out1"

        response_status['Activation_Type'] = inout

        response_status['Overlay_Type'] = type

        if type == "ticker":
            ticker_title = html5_json['ticker_title']
            ticker_text = html5_json['ticker_text']
            ticker_speed = html5_json['ticker_speed']
            composition_name = "Baseline - Crawl"

            # find the right composition
            for i in range(0,len(compositions)):
                composition = compositions[i]
                if composition['compositionName'] == composition_name:
                    if inout == "In":
                        # we are enabling overlay with features
                        del composition['animation']['state']
                        composition['animation']['action'] = 'play'
                        composition['animation']['to'] = inout
                        composition['controlNode']['payload']['Ticker Text'] = ticker_text
                        composition['controlNode']['payload']['Ticker Text Speed'] = ticker_speed
                        composition['controlNode']['payload']['Title'] = ticker_title
                    else:
                        # we are deactivating overlay
                        del composition['animation']['state']
                        composition['animation']['action'] = 'play'
                        composition['animation']['to'] = inout

                    key_composition = composition
        elif "score" in type:
            team_1_name = html5_json['team_1_name']
            team_2_name = html5_json['team_2_name']
            team_1_score = html5_json['team_1_score']
            team_2_score = html5_json['team_2_score']
            match_clock_start = html5_json['match_clock_start']
            match_clock_minutes = match_clock_start.split(":")[0]
            match_clock_seconds = match_clock_start.split(":")[1]
            match_clock_control = html5_json['match_clock_control']
            match_half = html5_json['match_half']
            composition_name = "Score Bug - Soccer"

            # find the right composition
            for i in range(0,len(compositions)):
                composition = compositions[i]
                if composition['compositionName'] == composition_name:
                    if inout == "In":
                        # we are enabling overlay with features

                        if type == "score":

                            del composition['animation']['state']
                            composition['animation']['action'] = 'play'
                            composition['animation']['to'] = inout
                            composition['controlNode']['payload']['Team 1 Name'] = team_1_name
                            composition['controlNode']['payload']['Team 1 Score'] = team_1_score
                            composition['controlNode']['payload']['Team 2 Name'] = team_2_name
                            composition['controlNode']['payload']['Team 2 Score'] = team_2_score
                            composition['controlNode']['payload']['Match Clock - Minutes'] = str(int(match_clock_minutes))
                            composition['controlNode']['payload']['Match Clock - Seconds'] = str(int(match_clock_seconds))
                            composition['controlNode']['payload']['Half'] = match_half
                            composition['controlNode']['payload']['Match Clock - Control']['isRunning'] = False
                            composition['controlNode']['payload']['Match Clock - Control']['value'] = 0

                            # configure clock
                            epoch_time_now = math.floor(time.time()) * 1000
                            #start_epoch_time = (int(epoch_time_now) - ( int(match_clock_minutes) * 60 ) - int(match_clock_seconds)) + int(composition['controlNode']['payload']['Match Clock - Control']['value'])
                            start_epoch_time = int(epoch_time_now) - ((( int(match_clock_minutes) * 60 ) - int(match_clock_seconds)) * 1000 )

                            composition['controlNode']['payload']['Match Clock - Control']['UTC'] = start_epoch_time
                        elif type == "score-score1update":
                            # update score for team 1
                            composition['controlNode']['payload']['Team 1 Score'] = team_1_score

                        elif type == "score-score2update":
                            # update score for team 2
                            composition['controlNode']['payload']['Team 2 Score'] = team_2_score

                        elif type == "score-matchcontrolstart":
                            # change isrunning to true
                            composition['controlNode']['payload']['Match Clock - Control']['isRunning'] = True

                            # calculate start time of clock
                            epoch_time_now = math.floor(time.time()) * 1000 #datetime.datetime.utcnow().strftime('%s') * 1000
                            clock_time_epochms = ((int(match_clock_minutes) * 60) + int(match_clock_seconds)) * 1000

                            start_epoch_time = int(epoch_time_now) - int(clock_time_epochms) - int(composition['controlNode']['payload']['Match Clock - Control']['value'])


                            composition['controlNode']['payload']['Match Clock - Control']['UTC'] = start_epoch_time
                            composition['controlNode']['payload']['Match Clock - Control']['value'] = 0


                        elif type == "score-matchcontrolstop":
                            # stop clock and put epoch value of elapsed time in the value field
                            composition['controlNode']['payload']['Match Clock - Control']['isRunning'] = False

                            # calculate pause time value
                            epoch_time_now = math.floor(time.time()) * 1000
                            pause_time = int(epoch_time_now) - int(composition['controlNode']['payload']['Match Clock - Control']['UTC'])

                            composition['controlNode']['payload']['Match Clock - Control']['UTC'] = epoch_time_now
                            composition['controlNode']['payload']['Match Clock - Control']['value'] = pause_time


                        elif type == "score-matchcontrolreset":
                            # reset and change running value to false
                            composition['controlNode']['payload']['Match Clock - Control']['isRunning'] = False

                            epoch_time_now = math.floor(time.time()) * 1000
                            startover_epoch_time = int(epoch_time_now) - ((( int(match_clock_minutes) * 60 ) - int(match_clock_seconds)) * 1000 )

                            composition['controlNode']['payload']['Match Clock - Control']['UTC'] = startover_epoch_time
                            composition['controlNode']['payload']['Match Clock - Control']['value'] = 0


                    else:
                        # we are deactivating overlay
                        del composition['animation']['state']
                        composition['animation']['action'] = 'play'
                        composition['animation']['to'] = inout

                    key_composition = composition

        elif type == "lthird":
            line_1_text = html5_json['line_1_text']
            line_2_text = html5_json['line_2_text']
            composition_name = "Lower - 2 Line"

            # find the right composition
            for i in range(0,len(compositions)):
                composition = compositions[i]
                if composition['compositionName'] == composition_name:
                    if inout == "In":
                        # we are enabling overlay with features
                        del composition['animation']['state']
                        composition['animation']['action'] = 'play'
                        composition['animation']['to'] = inout
                        composition['controlNode']['payload']['Line One Text'] = line_1_text
                        composition['controlNode']['payload']['Line Two Text'] = line_2_text
                    else:
                        # we are deactivating overlay
                        del composition['animation']['state']
                        composition['animation']['action'] = 'play'
                        composition['animation']['to'] = inout

                    key_composition = composition

        else: # "social-bug"
            social_url = html5_json['social_url']
            social_text = html5_json['social_text']
            composition_name = "Bug - Social"

            # find the right composition
            for i in range(0,len(compositions)):
                composition = compositions[i]
                if composition['compositionName'] == composition_name:
                    if inout == "In":
                        # we are enabling overlay with features
                        del composition['animation']['state']
                        composition['animation']['action'] = 'play'
                        composition['animation']['to'] = inout
                        composition['controlNode']['payload']['socialMediaLogo'] = social_url
                        composition['controlNode']['payload']['text'] = social_text
                    else:
                        # we are deactivating overlay
                        del composition['animation']['state']
                        composition['animation']['action'] = 'play'
                        composition['animation']['to'] = inout

                    key_composition = composition

        response_status['Composition_Body'] = key_composition

        new_compositions = []
        new_compositions.append(key_composition)
        new_compositions = json.dumps(new_compositions)

        # Update the html5 render via API
        put_response = http.request('PUT', html5_endpoint,body=new_compositions,headers={"Content-Type": "application/json"})

        response_status['htmlUpdateResponseCode'] = put_response.status

        return response_status

    ### END OF FUNCTIONS ###


    if functiontorun == "getSchedule":
        response = getSchedule()
        return api_response(200,response)
    elif functiontorun == "s3GetAssetList":
        response = s3GetAssetList()
        return api_response(200,response)
    elif functiontorun == "followCurrent":
        response = followCurrent()
        return api_response(200,response)
    elif functiontorun == "followLast":
        response = followLast()
        return api_response(200,response)
    elif functiontorun == "followCustom":
        response = followCustom()
        return api_response(200,response)
    elif functiontorun == 'immediateContinue':
        response = immediateContinue()
        return api_response(200,response)
    elif functiontorun == "immediateSwitch":
        response = immediateSwitch()
        return api_response(200,response)
    elif functiontorun == "getAttachedInputs":
        response = getLiveInputs()
        return api_response(200,response)
    elif functiontorun == "immediateSwitchLive":
        response = immediateSwitchLive()
        return api_response(200,response)
    elif functiontorun == "scteInject":
        response = scteInject()
        return api_response(200,response)
    elif functiontorun == "channelStartStop":
        response = channelStartStop()
        return api_response(200,response)
    elif functiontorun == "channelState":
        response = channelState()
        return api_response(200,response)
    elif functiontorun == "describeChannelState":
        response = describeChannelState()
        return api_response(200,response)
    elif functiontorun == "inputPrepare":
        response = inputPrepare()
        return api_response(200,response)
    elif functiontorun == "presignGenerator":
        response = presignGenerator()
        return api_response(200,response)
    elif functiontorun == "gfxActivate":
        response = gfxActivate()
        return api_response(200,response)
    elif functiontorun == "gfxDeactivate":
        response = gfxActivate()
        return api_response(200,response)
    elif functiontorun == "html5Activate":
        response = html5Activate()
        return api_response(200,response)
    elif functiontorun == "channelReservation":
        response = channelReservation()
        return api_response(200,response)
    elif functiontorun == "html5Graphics":
        response = html5Graphics()
        return api_response(200,response)

    else: # return error#
        response = {"error":"invalid functiontorun value sent to function"}
        return api_response(500,response)