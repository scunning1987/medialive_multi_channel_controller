import json
import boto3
import logging
import os

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TAGNAME = os.environ['TAGKEY']

def lambda_handler(event, context):

    regions = ['us-west-2','us-east-1']

    LOGGER.info("Initializing MediaLive Schedule Cleanup Script...")
    LOGGER.info("Regions to scan : %s " % (regions))

    for region in regions:

        LOGGER.info("Iterating through region: %s" % (region))

        # initialize boto3 client for region
        medialive_client = boto3.client('medialive',region_name=region)

        # capture channel response to variable
        medialive_channels = medialive_client.list_channels(MaxResults=100)

        if len(medialive_channels['Channels']) < 1:
            LOGGER.info("No medialive channels present in region : %s " % (region) )

        else:

            LOGGER.info("Found %s MediaLive channels in %s" % (len(medialive_channels['Channels']),region))

            # Iterate through returned channels
            for channel in medialive_channels['Channels']:

                # Do check for Tags attached to channel. Only delete schedule actions for channels part of the correct project
                if len(channel['Tags']) == 0 or TAGNAME not in channel['Tags']:
                    LOGGER.info("Channel %s not a part of bumpers workflow and so taking no action..." % (channel['Id']))

                else:

                    channel_id = channel['Id']

                    # Describe channel to get current active input
                    channel_details = medialive_client.describe_channel(ChannelId=channel_id)

                    if len(channel_details['PipelineDetails']) == 0:
                        # no active input / new channel
                        active_input_switch_name = ""

                    else:
                        active_input_switch_name = channel_details['PipelineDetails'][0]['ActiveInputSwitchActionName']

                    # Get channel schedule
                    channel_schedule = medialive_client.describe_schedule(ChannelId=channel_id,MaxResults=1000)

                    # iterate through schedule and delete all except current active input switch
                    if len(channel_schedule['ScheduleActions']) == 0:
                        LOGGER.info("No schedule actions for channel %s " % (channel_id))

                    actions_to_delete = []
                    actions_to_delete.clear()
                    for schedule_item in channel_schedule['ScheduleActions']:
                        action_name = schedule_item['ActionName']



                        if action_name != active_input_switch_name:
                            actions_to_delete.append(action_name)

                    if channel_details['State'] == "IDLE":

                        # If channel is idle we can delete all schedule actions at once
                        LOGGER.info("Channel %s is idle, doing bulk delete on schedule actions. %s actions to delete" % (channel_id,str(len(actions_to_delete))))
                        try:
                            channel_actions_delete = medialive_client.batch_update_schedule(ChannelId=channel_id,Deletes={'ActionNames': actions_to_delete})
                        except Exception as e:
                            LOGGER.error("Unable to delete channel actions, got exception : %s " % (e))

                    else:
                        # Channel not idle, best to use caution and delete schedule actions one by one, avoiding attempts to delete active or referenced schedule actions
                        for action_to_delete in actions_to_delete:
                            LOGGER.info("Deleting action name %s for channel %s " % (action_to_delete,channel_id))
                            try:
                                channel_actions_delete = medialive_client.batch_update_schedule(ChannelId=channel_id,Deletes={'ActionNames': [action_name]})
                            except Exception as e:
                                LOGGER.error("Unable to delete channel actions, got exception : %s " % (e))

    return "MediaLive Channel Schedule cleanup complete"