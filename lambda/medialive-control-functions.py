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
env variables: none
'''
import json
import boto3
import datetime
import random
import time
import os

def lambda_handler(event, context):
    
    print("INFO : Event Details - ",event)
    
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

    zixi_cidr = os.environ['ZIXI_RECEIVER_CIDR']
    zixi_remote_id = os.environ['ZIXI_REMOTE_ID']
    zixi_stream_id = os.environ['ZIXI_STREAM_ID']
    station_list = os.environ['STATION_LIST'].split(',')
    zixi_ip = os.environ['ZIXI_IP']
    ###
    
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
                    liveinputs.append({'name' : channel['Name'], 'type' : channel['Type']})
                    liveinputslist.append(channel['Name'])
                if "DYNAMIC" in channel['InputSourceType']:
                    fileinputs.append(channel['Name'])
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
    
            if len(schedule) is 0:
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

        if type == "immediate-continue":
            # Find a CONTINUE dynamic file (For promo / play once functionality)
            for input in input_attachments:
                if input['InputSettings']['SourceEndBehavior'] == "CONTINUE" and input['InputAttachmentName'] in inputs['file']:
                    inputattachref = input['InputAttachmentName']
        elif type == "live":
            inputattachref = inputkey
        elif type == "follow-live":
            inputattachref = inputfile
        else:
            # Find a LOOP attached dynamic file (For Slate loop functionality)
            for input in input_attachments:
                if input['InputSettings']['SourceEndBehavior'] == "LOOP" and input['InputAttachmentName'] in inputs['file']:
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
                                    'InputAttachmentNameReference': inputkey
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
        currentaction = channel_info['PipelineDetails'][0]['ActiveInputSwitchActionName'] # return string of current running action
        itemstoreplace = describe_schedule(inputs, currentaction, "true") # return dictionary : *itemstoreschedule*, itemstodelete, dashboardlist, lastaction
        channel_input_attachments = channel_info['InputAttachments']
        
        batch_update("immediate", "", inputs, inputkey,channel_input_attachments)
        
        for item in itemstoreplace['itemstoreschedule']:
            lastaction = describe_schedule(inputs, currentaction, "false") # return dictionary : itemstoreschedule, itemstodelete, dashboardlist, *lastaction*
            batch_update("follow", lastaction['lastaction'], inputs, item,channel_input_attachments)
        return itemstoreplace
    
    def immediateSwitchLive():
        inputs = list_inputs("dictionary") # return dictionary : file, live, livelist
        return batch_update("live", "", inputs, inputkey, "")

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
        batch_update("immediate-continue", "", inputs, input,channel_input_attachments)
        
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
                
                # schedule immediate swith to slate:
                slate_path = event['bucket'].split(":")[1].replace("%2F","/")
                inputs = list_inputs("dictionary") # return dictionary : file, live, livelist
                
                batch_update("immediate", "", inputs, slate_path,channel_input_attachments)
                
                ## start api
                response = client.start_channel(ChannelId=channelid)
                
                cw_client = boto3.client('events',region_name=region)
                event_put_response = cw_client.put_events(
                Entries=[
                    {
                        "Source": "lambda.amazonaws.com",
                        "DetailType": "MediaLive Channel State Change",
                        "Detail": "{\"state\":\"STARTING\",\"channel_arn\":\"channel:" + channelid + "\"}"
                    },
                ]
                )
                print("INFO : CW Event Put Response - ",event_put_response)
                return response
        else: # input is stop
            if channel_status == "IDLE" or channel_status == "STOPPING":
                return "Channel already stopping or stopped"
            else:
                # stop api
                response = client.stop_channel(ChannelId=channelid)
                
                cw_client = boto3.client('events',region_name=region)
                event_put_response = cw_client.put_events(
                Entries=[
                    {
                        "Source": "lambda.amazonaws.com",
                        "DetailType": "MediaLive Channel State Change",
                        "Detail": "{\"state\":\"STOPPING\",\"channel_arn\":\"channel:" + channelid + "\"}"
                    },
                ]
                )
                print("INFO : CW Event Put Response - ",event_put_response)
                #return channel_status
                return response
    
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
        
    def getEntitlementArn(station_code):
        response = emxclient.list_entitlements(MaxResults=20)
        entitlement_list = response['Entitlements']
        
        entitlement_arn = ""
        for entitlement in entitlement_list:
            if station_code in entitlement['EntitlementName']:
                entitlement_arn = entitlement['EntitlementArn']
        return entitlement_arn
    
    def createFlow(entitlement_arn,station_code):
        print("Create flow function")
        
        response = emxclient.create_flow(
            Name='MyZixiFlow',
            Outputs=[
            {   
                'CidrAllowList': [
                '0.0.0.0/0',
            ],
                'Description': 'output to zixi receiver',
                'Name': flow_destination,
                'Protocol': 'zixi-pull',
                'StreamId': flow_destination,
                'RemoteId':zixi_remote_id
            },
            ],
            Source={
                'Description': 'station',
                'EntitlementArn': entitlement_arn,
                'Name': 'EntitledSource',
            })
        return response
            
    def startFlow(flow_arn):
        print("start flow function")
        response = emxclient.start_flow(FlowArn=flow_arn)
        return response
        
    def listFlows():
        print("list flows")
        response = emxclient.list_flows(MaxResults=123)
        return response
        
    def deleteFlow(flow_arn):
        response = emxclient.delete_flow(FlowArn=flow_arn)
        return response
        
    ## END OF FUNCTIONS
    
    if flow_action == "startflow":
        print("INFO : Attempting to start flow - MyZixiFlow")
        print("INFO : Getting list of flows to see if MyZixiFlow exists...")
        
        entitlement_arn = getEntitlementArn(station_code)
        flow_list = listFlows()
        flow_exists = 0
        flow_details = []
        for flow in flow_list['Flows']:
            if flow['Name'] == "MyZixiFlow":
                flow_exists = 1
                flow_details = flow
                
        if flow_exists == 1:
            # Just Edit Flow's Source ARN
            print("INFO : MyZixiFlow Flow exists.. Moving on to amend source arn with selected entitlement arn %s" % (entitlement_arn))
            flow_arn = flow_details['FlowArn']
        
            response = emxclient.describe_flow(FlowArn=flow_arn)
            
            # Check if source is already set to the entitlement arn desired
            if "EntitlementArn" in response['Flow']['Source'].keys():
                if response['Flow']['Source']['EntitlementArn'] == entitlement_arn:
                    print("INFO: No action needed on amending source, flow entitlement arn is %s" % (response['Flow']['Source']['EntitlementArn']))
                    if response['Flow']['Status'] == "STANDBY":
                        return startFlow(flow_arn)
                    else:
                        return "INFO: Flow is active"
                else: 
                    source_arn = response['Flow']['Source']['SourceArn']
                    flow_status = response['Flow']['Status']
                    if flow_status != "STANDBY":
                        emxclient.stop_flow(FlowArn=flow_arn)
                    while flow_status != "STANDBY":
                        flow_details = emxclient.describe_flow(FlowArn=flow_arn)
                        flow_status = flow_details['Flow']['Status']
                        print("INFO: Flow must be in STANDBY state to be deleted; current status : %s" % (flow_status))
                        time.sleep(3)

                    response = emxclient.update_flow_source(EntitlementArn=entitlement_arn,FlowArn=flow_arn,SourceArn=source_arn)
                    if flow_status == "STANDBY":
                        return startFlow(flow_arn)
                    else:
                        return "INFO: Flow is active"
        else: 
            # Create a Flow
            if len(entitlement_arn) > 0:
                print("entitlement arn : %s" %(entitlement_arn))
                create_flow_response = createFlow(entitlement_arn,station_code)
                
                if create_flow_response['ResponseMetadata']['HTTPStatusCode'] == 201:
                    flow_arn = create_flow_response['Flow']['FlowArn']
                    return startFlow(flow_arn)
                else:
                    print("ERROR : Failed to Create flow : %s " % (create_flow_response))
                    return "ERROR : Failed to Create flow : %s " % (create_flow_response)
    
    elif flow_action == "stopflow":
        print("INFO : Stopping flow")
        
        flow_list = listFlows()
        flow_arn = ""
        flow_exists = 0
        for flow in flow_list['Flows']:
            if flow['Name'] == "MyZixiFlow":
                flow_arn = flow['FlowArn']
                flow_exists = 1
                print("INFO : Flow exists, the current state is %s" % (flow['Status']))
                if flow['Status'] == "ACTIVE":
                    print("INFO : Stopping the flow")
                    response = emxclient.stop_flow(FlowArn=flow_arn)
                    return response
                else:
                    print("INFO : Flow exists but is not in active state. Current state is %s" % (flow['Status']))
                    return "INFO : Flow exists but is not in active state. Current state is %s" % (flow['Status'])
        if flow_exists == 0:
            print("INFO : Flow doesn't exist. Nothing to stop...")
            return "INFO : Flow doesn't exist. Nothing to stop..."
    
    elif flow_action == "checkflow":
        print("INFO : Checking if flow exists and is currently outputting to the selected destination")
        
        flow_list = listFlows()
        flow_arn = ""
        flow_exists = 0
        
        for flow in flow_list['Flows']:
            if flow['Name'] == "MyZixiFlow":
                flow_arn = flow['FlowArn']
                flow_exists = 1
                print("INFO : Flow exists, the current state is %s" % (flow['Status']))
                if flow['Status'] == "ACTIVE":
                    # describe flow
                    response = emxclient.describe_flow(FlowArn=flow_arn)
                    flow_output_name = response['Flow']['Outputs'][0]['Name'].upper()
                    flow_source_name = response['Flow']['Source']['EntitlementArn'].split(":")[-1].upper()
                    print("INFO : Flow exists and is active, the current destination is %s" % (flow_output_name))
                    return {"flow_active":1,"flow_destination":flow_output_name,"flow_source":flow_source_name}
                else:
                    # exit
                    print("INFO : Flow exists but is not currently outputting")
                    return {"flow_active":0,"flow_destination":""}
        if flow_exists == 0:
            print("INFO : Flow doesnt exist")
            return {"flow_active":0,"flow_destination":""}
    
    
    if functiontorun == "getSchedule":
        return getSchedule()
    elif functiontorun == "s3GetAssetList":
        return s3GetAssetList()
    elif functiontorun == "followCurrent":
        return followCurrent()
    elif functiontorun == "followLast":
        return followLast()
    elif functiontorun == "followCustom":
        return followCustom()
    elif functiontorun == 'immediateContinue':
        return immediateContinue()
    elif functiontorun == "immediateSwitch":
        return immediateSwitch()
    elif functiontorun == "getAttachedInputs":
        return getLiveInputs()
    elif functiontorun == "immediateSwitchLive":
        return immediateSwitchLive()
    elif functiontorun == "scteInject":
        return scteInject()
    elif functiontorun == "channelStartStop":
        return channelStartStop()
    elif functiontorun == "channelState":
        return channelState()
    elif functiontorun == "startflow":
        print("INFO : Attempting to start flow - MyZixiFlow")
        print("INFO : Getting list of flows to see if MyZixiFlow exists...")
        
        entitlement_arn = getEntitlementArn(station_code)
        flow_list = listFlows()
        flow_exists = 0
        flow_details = []
        for flow in flow_list['Flows']:
            if flow['Name'] == "MyZixiFlow":
                flow_exists = 1
                flow_details = flow
                
        if flow_exists == 1:
            # Just Edit Flow's Source ARN
            print("INFO : MyZixiFlow Flow exists.. Moving on to amend source arn with selected entitlement arn %s" % (entitlement_arn))
            flow_arn = flow_details['FlowArn']
        
            response = emxclient.describe_flow(FlowArn=flow_arn)
            
            # Check if source is already set to the entitlement arn desired
            if "EntitlementArn" in response['Flow']['Source'].keys():
                if response['Flow']['Source']['EntitlementArn'] == entitlement_arn:
                    print("INFO: No action needed on amending source, flow entitlement arn is %s" % (response['Flow']['Source']['EntitlementArn']))
                    if response['Flow']['Status'] == "STANDBY":
                        return startFlow(flow_arn)
                    else:
                        return "INFO: Flow is active"
                else: 
                    source_arn = response['Flow']['Source']['SourceArn']
                    flow_status = response['Flow']['Status']
                    if flow_status != "STANDBY":
                        emxclient.stop_flow(FlowArn=flow_arn)
                    while flow_status != "STANDBY":
                        flow_details = emxclient.describe_flow(FlowArn=flow_arn)
                        flow_status = flow_details['Flow']['Status']
                        print("INFO: Flow must be in STANDBY state to be deleted; current status : %s" % (flow_status))
                        time.sleep(3)

                    response = emxclient.update_flow_source(EntitlementArn=entitlement_arn,FlowArn=flow_arn,SourceArn=source_arn)
                    if flow_status == "STANDBY":
                        return startFlow(flow_arn)
                    else:
                        return "INFO: Flow is active"
        else: 
            # Create a Flow
            if len(entitlement_arn) > 0:
                print("entitlement arn : %s" %(entitlement_arn))
                create_flow_response = createFlow(entitlement_arn,station_code)
                
                if create_flow_response['ResponseMetadata']['HTTPStatusCode'] == 201:
                    flow_arn = create_flow_response['Flow']['FlowArn']
                    return startFlow(flow_arn)
                else:
                    print("ERROR : Failed to Create flow : %s " % (create_flow_response))
                    return "ERROR : Failed to Create flow : %s " % (create_flow_response)
    
    elif functiontorun == "stopflow":
        print("INFO : Stopping flow")
        
        flow_list = listFlows()
        flow_arn = ""
        flow_exists = 0
        for flow in flow_list['Flows']:
            if flow['Name'] == "MyZixiFlow":
                flow_arn = flow['FlowArn']
                flow_exists = 1
                print("INFO : Flow exists, the current state is %s" % (flow['Status']))
                if flow['Status'] == "ACTIVE":
                    print("INFO : Stopping the flow")
                    response = emxclient.stop_flow(FlowArn=flow_arn)
                    return response
                else:
                    print("INFO : Flow exists but is not in active state. Current state is %s" % (flow['Status']))
                    return "INFO : Flow exists but is not in active state. Current state is %s" % (flow['Status'])
        if flow_exists == 0:
            print("INFO : Flow doesn't exist. Nothing to stop...")
            return "INFO : Flow doesn't exist. Nothing to stop..."
    
    elif functiontorun == "checkflow":
        print("INFO : Checking if flow exists and is currently outputting to the selected destination")
        
        flow_list = listFlows()
        flow_arn = ""
        flow_exists = 0
        
        for flow in flow_list['Flows']:
            if flow['Name'] == "MyZixiFlow":
                flow_arn = flow['FlowArn']
                flow_exists = 1
                print("INFO : Flow exists, the current state is %s" % (flow['Status']))
                if flow['Status'] == "ACTIVE":
                    # describe flow
                    response = emxclient.describe_flow(FlowArn=flow_arn)
                    flow_output_name = response['Flow']['Outputs'][0]['Name'].upper()
                    print("INFO : Flow exists and is active, the current destination is %s" % (flow_output_name))
                    return {"flow_active":1,"flow_destination":flow_output_name}
                else:
                    # exit
                    print("INFO : Flow exists but is not currently outputting")
                    return {"flow_active":0,"flow_destination":""}
        if flow_exists == 0:
            print("INFO : Flow doesnt exist")
            return {"flow_active":0,"flow_destination":""}
        
    else: # return error
        return "invalid functiontorun value sent to function"
