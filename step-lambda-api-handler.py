import json
import boto3
import os
import logging
import datetime
import re
import logging
import base64

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
db_client = boto3.client('dynamodb')
cw_client = boto3.client('events')
dynamodb_table_name = os.environ['VideoPipelineDatabase']
exceptions = []
default_region = "us-west-2"

def lambda_handler(event, context):

    def api_response(response_code,response_body):
        return {
            'statusCode': response_code,
            'body': json.dumps(response_body)
        }

    # enable for event debugging
    #return api_response(200,event)

    LOGGER.debug(event)
    current_time = str(datetime.datetime.now())


    # channels = event['channels']
    # region = event['region']
    # pipeline = event['pipeline']

    api_call_validation = []

    # get request time
    event['requestContext']['requestTime'] = current_time

    httpMethod = event['httpMethod']

    ## Validate Path first
    request_path = event['path']
    if request_path != "/dashboard-workflow":
        msg = "Request path submitted does not equal a supported function, available options are: /dashboard-workflow"
        LOGGER.error(msg)
        api_call_validation.append(msg)
        return api_response(500,{"status":api_call_validation})

    # check if query parameters were sent in the request
    if event['queryStringParameters'] is None:
        msg = "Request does not include query string parameters required for this function"
        LOGGER.error(msg)
        api_call_validation.append(msg)
        return api_response(500,{"status":api_call_validation})

    request_query_strings = event['queryStringParameters']


    ## Extract task from query paramaters
    try:
        task = request_query_strings['task']
    except Exception as e:
        msg = "Unable to extract task query parameter from request: %s " % (e)
        LOGGER.error(msg)
        api_call_validation.append(msg)
        return api_response(500,{"status":api_call_validation})



    ###
    ### VALIDATION STEPS
    ###

    # Validate the task query param value
    valid_task_values = ['create', 'delete', 'start', 'stop', 'list']

    if task not in valid_task_values:
        msg = "Task value submitted does not equal a supported function, available options are: create, delete, start, stop, list"
        LOGGER.error(msg)
        api_call_validation.append(msg)
        return api_response(500,{"status":api_call_validation})

    # Validate the value of channels
    if task == "create" or task == "delete":
        LOGGER.info("API Call received to %s a deployment" % (task))

        # get: name , channels, region
        ## Extract name from query paramaters
        try:
            name = request_query_strings['name']
        except Exception as e:
            msg = "Unable to extract name query parameter from request: %s " % (e)
            LOGGER.error(msg)
            api_call_validation.append(msg)
            return api_response(500,{"status":api_call_validation})

    if task == "create":
        ## Extract channels from query paramaters
        try:
            channels = request_query_strings['channels']
        except Exception as e:
            msg = "Unable to extract channels query parameter from request: %s " % (e)
            LOGGER.error(msg)
            api_call_validation.append(msg)
            return api_response(500,{"status":api_call_validation})


        # Need to make sure CHANNELS value is specified and is a valid integer
        try:
            channels = int(channels)
        except Exception as e:
            msg = "Cannot create deployment, invalid number for channels to create : %s " % (str(channels))
            LOGGER.error(msg)
            api_call_validation.append(msg)
            return api_response(500,{"status":api_call_validation})

    # Validate that the name parameter contains a value. We won't look up DynamoDB for an entry right now, this is just for query param validation
    if task != "list":
        if len(name) == 0:
            msg = "Cannot %s deployment, no name has been passed in the query string" %s (task)
            LOGGER.error(msg)
            api_call_validation.append(msg)
            return api_response(500,{"status":api_call_validation})

    # Validate correct region was specified
    emx_regions = [ "us-east-1", "us-east-2", "us-west-1", "us-west-2", "ap-east-1", "ap-south-1", "ap-northeast-2", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1","eu-central-1", "eu-west-1","eu-west-2", "eu-west-3", "eu-north-1","sa-east-1"]

    ## Extract region from query paramaters
    try:
        region = request_query_strings['region']
    except Exception as e:
        msg = "Unable to extract region query parameter from request: %s , defaulting to us-west-2" % (e)
        LOGGER.warning(msg)
        region = ""

    if len(region) < 1:
        # Default to region us-west-2
        region = default_region
    elif region not in emx_regions: # Check validity of region
        msg = "Cannot create deployment, region specified was incorrect : %s , valid regions : %s " % (region, emx_regions)
        LOGGER.error(msg)
        api_call_validation.append(msg)
        return api_response(500,{"status":api_call_validation})


    ## Extract pipeline from query paramaters
    try:
        pipeline = request_query_strings['pipeline']
    except Exception as e:
        msg = "Unable to extract pipeline query parameter from request: %s , defaulting to SINGLE_PIPELINE" % (e)
        LOGGER.warning(msg)
        pipeline = ""

    if len(pipeline) > 0:
        pipeline = "STANDARD"
    else:
        pipeline = "SINGLE_PIPELINE"

    # Need to obtain channel creation data
    try:
        channel_data = request_query_strings['channel_data']
    except Exception as e:
        msg = "Unable to get channel_data key from request, continuing with empty channel data. Default create behavior will be to deploy OTT HD channels only : %s " % (e)
        LOGGER.warning(msg)
        channel_data = ""


    # Parse the channel put data if present
    if task == "create" and httpMethod == "PUT":
        if "body" in list(event.keys()):

            if event['isBase64Encoded']:
                channel_data = json.loads(base64.b64decode(event['body']).decode("utf-8"))
            else:
                channel_data = event['body']
        else:
            channel_data = ""

    ###
    ### If the function reaches here, then valid values were received
    ###

    ###
    ### Function Code Block = START
    ###

    # check task == either of these values:
    # 'create' 'delete' 'start' 'stop' 'list'

    # create
    # 1. check DynamoDB to see if TABLE, then item exists
    # 2. if doesn't exist, create item with attached template
    # 3. send task to Step Functions
    # 4. if any caught exceptions from 1-3 ; try to undo DynamoDB creation (if that succeeded originally), else do 5.
    # 5. return to sender with "in progress" status

    ## Get list of DynamoDB Tables
    def listdbtables():
        LOGGER.info("Doing a LIST on DynamoDB tables to see if table exists")
        try:
            list_tables_response = db_client.list_tables(Limit=100)
            table_names = list_tables_response['TableNames']
            LOGGER.debug("DynamoDB list tables response : %s" % (list_tables_response))
        except Exception as e:
            LOGGER.error("Unable to check DynamoDB for tables. Please try again later, response : %s " % (e))
            exceptions.append(e)
            return e
        LOGGER.info("Completed DynamoDB List task")
        return table_names

    def createdbtable():
        LOGGER.info("Creating DB Table as it does not exist")
        try:
            attribute_definitions = [{'AttributeName': 'Group_Name','AttributeType': 'S'}]
            key_schema = [{'AttributeName': 'Group_Name','KeyType': 'HASH'}]
            create_db_response = db_client.create_table(TableName=dynamodb_table_name,AttributeDefinitions=attribute_definitions,KeySchema=key_schema,BillingMode='PAY_PER_REQUEST')
            LOGGER.debug("DynamoDB create DB response : %s " % (create_db_response))
        except Exception as e:
            LOGGER.error("Unable to check DynamoDB for tables. Please try again later, response : %s " % (e))
            exceptions.append(e)
            return e
        return create_db_response

    def listitems():
        LOGGER.info("Getting a list of items in database")
        try:
            query_response = db_client.scan(TableName=dynamodb_table_name)
            LOGGER.debug("DynamoDB scan response : %s" % (query_response))
        except Exception as e:
            LOGGER.error("Unable to check DynamoDB table for items. Please try again later, response : %s " % (e))
            exceptions.append(e)
            return e
        return query_response

    def itemcheck(query_response):
        duplicate_check = False

        for item in query_response['Items']:
            if name == item['Group_Name']['S']:
                duplicate_check = True

        ## If the item exists. fail now
        if duplicate_check:
            LOGGER.warning("Found deployment name in database")
            #exceptions.append("WARNING: Found deployment name in database")
            return True
        else:
            return False

    def createitem():
        # Create DB Item for deployment
        LOGGER.info("name does not exist in database. attempting to create now")

        json_item = dict()
        json_item['Group_Name'] = name
        json_item['Channels'] = str(channels)
        json_item['Region'] = region
        json_item['Pipeline'] = pipeline

        dynamodb_item = dict()
        json_to_dynamo(dynamodb_item,json_item)

        try:
            put_item_response = db_client.put_item(TableName=dynamodb_table_name,Item=dynamodb_item)
            LOGGER.debug("DynamoDB Put Item response: %s" % (put_item_response))
        except Exception as e:
            msg = "Unable to create item in database. Please try again later, response : %s " % (e)
            LOGGER.error(msg)
            exceptions.append(msg)
            return api_response(500,{"status":exceptions})

    def triggerStepFunctions(cwatch_event):
        LOGGER.info("Completed all api handler tasks, now initiating Step Functions to complete the video deployment tasks for action : %s " % (task))

        try:
            LOGGER.info("Data to start Step Functions State Machine : %s " % (cwatch_event))
            response = cw_client.put_events(Entries=[{
                "Source": "lambda.amazonaws.com",
                "DetailType": "StepFunctionsTrigger",
                "Detail": json.dumps(cwatch_event)
            },])
            LOGGER.debug("CloudWatch Event Put response : %s " % (response))
        except Exception as e:
            LOGGER.error("Unable to Initiate Step Function via CloudWatch Event, exception : %s" % (e))
            exceptions.append(e)
            return e
            ## Need to destroy any item creation now.
        LOGGER.info("Successfully sent task to Step Functions")
        return response


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
    ### Function Code Block = END
    ###

    ## If we get to here any everything is ok, we now initiate the call to Step Functions
    ## Need to trigger step functions with a CloudWatch Event


    # ['create', 'delete', 'start', 'stop', 'list']
    exceptions.clear()

    if task == "create":
        # do stuff
        table_names = listdbtables()

        if len(exceptions) > 0:
            return api_response(500,exceptions)
        if dynamodb_table_name not in table_names:
            LOGGER.info("Database exists, moving on...")
            ## Need to create a new DynamoDB table
            createdbtable()
            if len(exceptions) > 0:
                return api_response(500,exceptions)
        else:
            ### table exists, check for item
            LOGGER.info("Database exists. Looking for item...")

            query_response = listitems()

            if len(exceptions) > 0:
                return api_response(500,exceptions)

            itemexists = itemcheck(query_response)
            if len(exceptions) > 0:
                return api_response(500,exceptions)
            LOGGER.info("Does item exist in database: %s" % (str(itemexists)))
            if itemexists is True:
                exceptions.append("WARNING: Found deployment name in database")
                return api_response(500,exceptions)
            else:
                ### Need to put item in database
                createitem()
                if len(exceptions) > 0:
                    return api_response(500,exceptions)

        cwatch_event = {"task":task,"name":name,"channels":channels,"dynamodb_table_name":dynamodb_table_name,"channel_data":channel_data,"delete_tasks":{"medialive_channels":0,"medialive_inputs":0,"mediapackage_channels":0,"channel_map":0,}}
        triggerStepFunctions(cwatch_event)
        if len(exceptions) > 0:
            return api_response(500,exceptions)
        event['status'] = "IN PROGRESS"

        return api_response(200,{"status":"creation in progress"})

    elif task == "delete":
        # check if DB table exists
        table_names = listdbtables()
        if len(exceptions) > 0:
            return api_response(500,exceptions)
        if dynamodb_table_name not in table_names:
            exceptions.append("INFO: There are currently no deployments managed by ott auto")
            return api_response(500,exceptions)

        # check if deployment exists
        query_response = listitems()

        if len(exceptions) > 0:
            return api_response(500,exceptions)

        itemexists = itemcheck(query_response)

        if itemexists is False:
            exceptions.append("The name you specified doesnt exist as a deployment")
            return api_response(500,exceptions)

        # do stuff
        channels = ""
        cwatch_event = {"task":task,"name":name,"channels":channels,"dynamodb_table_name":dynamodb_table_name,"channel_data":channel_data,"delete_tasks":{"medialive_channels":0,"medialive_inputs":0,"mediapackage_channels":0,"channel_map":0,}}
        triggerStepFunctions(cwatch_event)
        if len(exceptions) > 0:
            return api_response(500,exceptions)
        event['status'] = "IN PROGRESS"
        return api_response(200,{"status":"deletion in progress"})

    elif task == "start":
        # check if DB table exists
        table_names = listdbtables()
        if len(exceptions) > 0:
            return api_response(500,exceptions)
        if dynamodb_table_name not in table_names:
            exceptions.append("INFO: There are currently no deployments managed by ott auto")
            return api_response(500,exceptions)

        # check if deployment exists

        query_response = listitems()

        if len(exceptions) > 0:
            return api_response(500,exceptions)

        itemexists = itemcheck(query_response)

        if itemexists is False:
            exceptions.append("The name you specified doesnt exist as a deployment")
            return api_response(500,exceptions)

        # do stuff
        cwatch_event = {"task":task,"name":name,"channels":channels,"dynamodb_table_name":dynamodb_table_name,"channel_data":channel_data,"delete_tasks":{"medialive_channels":0,"medialive_inputs":0,"mediapackage_channels":0,"channel_map":0,}}        triggerStepFunctions(cwatch_event)

        if len(exceptions) > 0:
            return api_response(500,exceptions)
        event['status'] = "IN PROGRESS"
        return api_response(200,{"status":"group start notification under way..."})

    elif task == "stop":
        # check if DB table exists
        table_names = listdbtables()
        if len(exceptions) > 0:
            return api_response(500,exceptions)
        if dynamodb_table_name not in table_names:
            exceptions.append("INFO: There are currently no deployments managed by ott auto")
            return api_response(500,exceptions)

        # check if deployment exists
        query_response = listitems()

        if len(exceptions) > 0:
            return api_response(500,exceptions)

        itemexists = itemcheck(query_response)
        if itemexists is False:
            exceptions.append("The name you specified doesnt exist as a deployment")
            return api_response(500,exceptions)

        # do stuff
        cwatch_event = {"task":task,"name":name,"channels":channels,"dynamodb_table_name":dynamodb_table_name,"channel_data":channel_data,"delete_tasks":{"medialive_channels":0,"medialive_inputs":0,"mediapackage_channels":0,"channel_map":0,}}
        triggerStepFunctions(cwatch_event)

        if len(exceptions) > 0:
            return api_response(500,exceptions)
        event['status'] = "IN PROGRESS"
        return api_response(200,{"status":"group start notification under way..."})

    elif task == "list":
        table_names = listdbtables()
        if len(exceptions) > 0:
            return api_response(500,exceptions)
        if dynamodb_table_name not in table_names:
            exceptions.append("INFO: Currently you have no deployments")
            return api_response(500,exceptions)

        # Get list of items in db = deployments
        dbitems = listitems()
        if len(exceptions) > 0:
            return api_response(500,exceptions)

        json_item = dict()
        dynamo_to_json(json_item,dbitems)

        return json_item

    else:
        return api_response(500,{"status":"no idea how you ended up here"})