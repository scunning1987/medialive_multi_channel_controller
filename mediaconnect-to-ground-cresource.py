import json
import boto3
import os
import logging
import cfnresponse

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def lambda_handler(event, context):
    LOGGER.info("Received custom resource event : %s" % (event))

    # Create Response Data Dictionary for the CloudFormationn response
    responseData = dict()

    # Flow Arn passed as env variable
    flow_arn = os.environ['FLOWARN']
    media_connect_flow_output_1 = os.environ['GROUNDLISTENER1']
    media_connect_flow_output_2 = os.environ['GROUNDLISTENER2']


    # Initialize boto3 MediaConnect client
    emx = boto3.client('mediaconnect')


    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
        ####
        #### CREATE
        ####

        ##### ADD VPC FLOW SOURCE

        try:

            LOGGER.info("Attempting to update source to use VPC interface...")

            # Describe flow
            response = emx.describe_flow(FlowArn=flow_arn)

            # flow name
            flow_name = response['Flow']['Name']

            # Source Arn
            flow_source_arn = response['Flow']['Sources'][0]['SourceArn']


            # Ingest Port
            ingest_port = response['Flow']['Sources'][0]['IngestPort']

            # VPC Interface
            vpc_interface_name = response['Flow']['VpcInterfaces'][0]['Name']

            # Update flow source #
            response = emx.update_flow_source(FlowArn=flow_arn,VpcInterfaceName=vpc_interface_name,SourceArn=flow_source_arn)

        except Exception as e:

            responseData['Status'] = "Unable to modify source, got exception : %s " % (e)
            LOGGER.error("Unable to modify source, got exception : %s " % (e))
            cfnresponse.send(event, context, "FAILED",responseData)

        ##### ADD VPC FLOW OUTPUT

        flow_outputs = []
        flow_outputs.append(media_connect_flow_output_1)
        flow_outputs.append(media_connect_flow_output_2)

        outputs = []

        try:

            LOGGER.info("Attempting to add VPC outputs...")

            for flow_output in flow_outputs:
                if ":" in flow_output:
                    ip = flow_output.split(":")[0]
                    port = flow_output.split(":")[1]
                    output_name = flow_name + ip.replace(".","") + port
                    LOGGER.info("VPC Output: %s:%s" % (ip,port))

                    output = dict()
                    output['Description'] = "Output to Bristol, IP %s and port %s" % (ip,port)
                    output['Destination'] = ip
                    output['Name'] = output_name
                    output['Port'] = int(port)
                    output['Protocol'] = "rtp-fec"

                    outputs.append(output)

            response = emx.add_flow_outputs(FlowArn=flow_arn,Outputs=outputs)
        except Exception as e:
            responseData['Status'] = "Unable to add VPC Outputs, got exception : %s " % (e)
            LOGGER.error("Unable to add VPC Outputs, got exception : %s " % (e))
            cfnresponse.send(event, context, "FAILED",responseData)

        responseData['Status'] = "SUCCESS"

        cfnresponse.send(event, context, "SUCCESS",responseData)
        return responseData

    elif event['RequestType'] == 'Delete':
        ####
        #### DELETE
        ####

        ##### ADD VPC FLOW SOURCE

        try:

            LOGGER.info("Attempting to delete VPC interface attached to flow...")

            # Describe flow
            response = emx.describe_flow(FlowArn=flow_arn)

            # flow name
            flow_name = response['Flow']['Name']

            # Source Arn
            flow_source_arn = response['Flow']['Sources'][0]['SourceArn']

            # Ingest Port
            ingest_port = response['Flow']['Sources'][0]['IngestPort']

            # Update flow source #
            response = emx.update_flow_source(FlowArn=flow_arn,SourceArn=flow_source_arn,Protocol='rtp-fec')

        except Exception as e:

            responseData['Status'] = "Unable to modify source, got exception : %s " % (e)
            LOGGER.error("Unable to modify source, got exception : %s " % (e))
            cfnresponse.send(event, context, "FAILED",responseData)

        cfnresponse.send(event, context, "SUCCESS",responseData)
        return responseData

    responseData['Status'] = "Did not receive good event RequestType"
    cfnresponse.send(event, context, "FAILED",responseData)
    return responseData