import json
import boto3
import os
import logging
import datetime
import re
import logging

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
db_client = boto3.client('dynamodb')
cw_client = boto3.client('events')
dynamodb_table_name = os.environ['VideoPipelineDatabase']
exceptions = []

def lambda_handler(event, context):

    LOGGER.debug(event)
    current_time = str(datetime.datetime.now())
    event['time'] = current_time
    channels = event['channels']
    region = event['region']
    pipeline = event['pipeline']

    task = event['task']
    try:
        channels = int(event['channels'])
    except:
        channels = ""

    name = event['name']

    api_call_validation = []
    valid_task_values = ['create', 'delete', 'start', 'stop', 'list']

    ###
    ### VALIDATION STEPS
    ###

    # Validate the task query param value
    if task not in valid_task_values:
        LOGGER.error("Task value submitted does not equal a supported function, available options are: create, delete, start, stop, list")
        api_call_validation.append("ERROR: Task value submitted does not equal a supported function, available options are: create, delete, start, stop, list")
        event['status'] = "ERROR: Task value submitted does not equal a supported function, available options are: create, delete, start, stop, list"
        return event

    # Validate the value of channels
    if task == "create":
        LOGGER.info("API Call received to CREATE a deployment")

        # Need to make sure CHANNELS value is specified and is a valid integer
        if isinstance(channels, int) is False:

            LOGGER.error("Cannot create deployment, invalid number for channels to create : %s " % (str(channels)))
            event['status'] = "ERROR : Cannot create deployment, please specify a valid number for channels to create"
            return event

    # Validate that the name parameter contains a value. We won't look up DynamoDB for an entry right now, this is just for query param validation
    if task != "list":
        if len(name) == 0:
            LOGGER.error("Cannot create deployment, no name has been passed for the deployment")
            event['status'] = "ERROR : Cannot create deployment, no name has been passed for the deployment"
            return event

    # Validate correct region was specified
    emx_regions = [ "us-east-1", "us-east-2", "us-west-1", "us-west-2", "ap-east-1", "ap-south-1", "ap-northeast-2", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1","eu-central-1", "eu-west-1","eu-west-2", "eu-west-3", "eu-north-1","sa-east-1"]

    if len(region) < 1:
        # Default to region us-west-2
        region = "us-west-2"
    elif region not in emx_regions: # Check validity of region
        LOGGER.error("Cannot create deployment, region specified was incorrect : %s" % (region))
        event['status'] = "ERROR : Cannot create deployment, region specified was incorrect : %s" % (region)
        return event

    if len(pipeline) > 0:
        pipeline = "STANDARD"
    else:
        pipeline = "SINGLE_PIPELINE"

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
            attribute_definitions = [{'AttributeName': 'Deployment_Name','AttributeType': 'S'}]
            key_schema = [{'AttributeName': 'Deployment_Name','KeyType': 'HASH'}]
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
            if name == item['Deployment_Name']['S']:
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

        # Edit the sample template with the new deployment name
        with open('item_template.json', 'r') as f:
            item_template_str = f.read()
        item_template = json.loads(item_template_str)

        item_template['Deployment_Name']['S'] = name
        item_template['Channels']['S'] = str(channels)
        item_template['Region']['S'] = str(region)
        item_template['Pipeline']['S'] = str(pipeline)

        try:
            put_item_response = db_client.put_item(TableName=dynamodb_table_name,Item=item_template)
            LOGGER.debug("DynamoDB Put Item response: %s" % (put_item_response))
        except Exception as e:
            LOGGER.error("Unable to create item in database. Please try again later, response : %s " % (e))
            exceptions.append(e)
            return e

    def triggerStepFunctions():
        LOGGER.info("Completed all api handler tasks, now initiating Step Functions to complete the video deployment tasks for action : %s " % (task))

        try:
            cwatch_event = {"task":task,"name":name,"channels":channels,"dynamodb_table_name":dynamodb_table_name}
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

    def errorOut():
        event['status'] = exceptions
        return event


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
                for i in range(0,len(v)):
                    dynamodb_item_list = dict()
                    json_to_dynamo(dynamodb_item_list,v[i])

                    v[i] = {"M":dynamodb_item_list}

                dicttopopulate.update({k:{"L":v}})

    # DYNAMODB_JSON_DECONSTRUCTOR
    def dynamo_to_json(dicttopopulate,my_dict):
        for k,v in my_dict.items():

            value_type = list(my_dict[k].keys())[0]

            if value_type == "M":
                value = my_dict[k][value_type]

                for i in range(0,len(value)):
                    dynamodb_item_m = dict()
                    dynamo_to_json(dynamodb_item_m,value)
                    v = dynamodb_item_m

                value.update(dynamodb_item_m)
                dicttopopulate.update({k:value})

            elif value_type == "S":
                value = my_dict[k][value_type]
                dicttopopulate.update({k:value})

            elif value_type == "L": # list
                value = my_dict[k][value_type]

                for i in range(0,len(value)):
                    dynamodb_item_list = dict()
                    dynamo_to_json(dynamodb_item_list,value[i])

                    value[i] = dynamodb_item_list

                dicttopopulate.update({k:value})
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
            return errorOut()
        if dynamodb_table_name not in table_names:
            LOGGER.info("Database exists, moving on...")
            ## Need to create a new DynamoDB table
            createdbtable()
            if len(exceptions) > 0:
                return errorOut()
        else:
            ### table exists, check for item
            LOGGER.info("Database exists. Looking for item...")

            query_response = listitems()

            if len(exceptions) > 0:
                return errorOut()

            itemexists = itemcheck(query_response)
            if len(exceptions) > 0:
                return errorOut()
            LOGGER.info("Does item exist in database: %s" % (str(itemexists)))
            if itemexists is True:
                exceptions.append("WARNING: Found deployment name in database")
                return errorOut()
            else:
                ### Need to put item in database
                createitem()
                if len(exceptions) > 0:
                    return errorOut()

        triggerStepFunctions()
        if len(exceptions) > 0:
            return errorOut()
        event['status'] = "IN PROGRESS"
        return event

    elif task == "delete":
        # check if DB table exists
        table_names = listdbtables()
        if len(exceptions) > 0:
            return errorOut()
        if dynamodb_table_name not in table_names:
            exceptions.append("INFO: There are currently no deployments managed by ott auto")
            return errorOut()

        # check if deployment exists
        query_response = listitems()

        if len(exceptions) > 0:
            return errorOut()

        itemexists = itemcheck(query_response)

        if itemexists is False:
            exceptions.append("The name you specified doesnt exist as a deployment")
            return errorOut()

        # do stuff
        triggerStepFunctions()
        if len(exceptions) > 0:
            return errorOut()
        event['status'] = "IN PROGRESS"
        return event

    elif task == "start":
        # check if DB table exists
        table_names = listdbtables()
        if len(exceptions) > 0:
            return errorOut()
        if dynamodb_table_name not in table_names:
            exceptions.append("INFO: There are currently no deployments managed by ott auto")
            return errorOut()

        # check if deployment exists

        query_response = listitems()

        if len(exceptions) > 0:
            return errorOut()

        itemexists = itemcheck(query_response)

        if itemexists is False:
            exceptions.append("The name you specified doesnt exist as a deployment")
            return errorOut()

        # do stuff
        triggerStepFunctions()
        if len(exceptions) > 0:
            return errorOut()
        event['status'] = "IN PROGRESS"
        return event

    elif task == "stop":
        # check if DB table exists
        table_names = listdbtables()
        if len(exceptions) > 0:
            return errorOut()
        if dynamodb_table_name not in table_names:
            exceptions.append("INFO: There are currently no deployments managed by ott auto")
            return errorOut()

        # check if deployment exists
        query_response = listitems()

        if len(exceptions) > 0:
            return errorOut()

        itemexists = itemcheck(query_response)
        if itemexists is False:
            exceptions.append("IThe name you specified doesnt exist as a deployment")
            return errorOut()

        # do stuff
        triggerStepFunctions()
        if len(exceptions) > 0:
            return errorOut()
        event['status'] = "IN PROGRESS"
        return event

    elif task == "list":
        table_names = listdbtables()
        if len(exceptions) > 0:
            return errorOut()
        if dynamodb_table_name not in table_names:
            exceptions.append("INFO: Currently you have no deployments")
            return errorOut()

        # Get list of items in db = deployments
        dbitems = listitems()
        if len(exceptions) > 0:
            return errorOut()
        prettyoutput = dict()

        for item in dbitems['Items']:
            deployment_name = item['Deployment_Name']['S']
            deployment_dashboard = item['CloudFront']['M']['Dashboard_URL']['S']
            prettyoutput.update({deployment_name:{'deployment_dashboard':deployment_dashboard}})
        return prettyoutput

    else:
        return "should not ever get here"