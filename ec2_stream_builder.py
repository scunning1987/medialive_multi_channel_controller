import json
import sys
import logging

# Create Logging Handler
LOGGER = logging.getLogger('Stream Builder')
LOGGER.setLevel(logging.INFO)

# Create File Handler For Logging
fh = logging.FileHandler('mpeg2-corrector.log') ## Un-comment this line when doing console testing
fh.setLevel(logging.DEBUG) ## Un-comment this line when doing console testing

# Create Console Handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter) #### Un-comment this line when doing console testing
ch.setFormatter(formatter)

# add the handlers to the logger
LOGGER.addHandler(fh) #### Un-comment this line when doing console testing
LOGGER.addHandler(ch)

udp_start_emx = 0
channel_count = 0

# Try incoming arguments or default to 50 and ports starting at 20001
try:
    channel_count = int(sys.argv[1])
    LOGGER.info("Channels to configure streamer for : %s " % (str(channel_count)))
    if int(sys.argv[1]) > 100:
        LOGGER.warning("Streamer supports max of 100 streams, defaulting to 100")
        channel_count = 100
except:
    LOGGER.warning("Received bad data, defaulting to 50 channels")
    # default
    channel_count = 40

try:
    udp_start_emx = int(sys.argv[2])
    LOGGER.info("Starting port number in range: %s , please make sure your EC2 security groups are set accordingly" % (str(udp_start_emx)))
    if int(udp_start_emx) < 5000:
        LOGGER.warning("Starting port set too low, defaulting to 20001")
        udp_start_emx = 20000
except:
    # default
    udp_start_emx = 20000

live_stream_app_name = "lowlatency"

cameras_list = []
streams_list = []
stream_source = [ "emx" , "eml" ]

# JSON to edit
template_rules_conf_json = {
    "SyncResponse": {
        "status": "success",
        "StreamCheckerMode": "false",
        "UniqueVisitors": "false",
        "RoutesHash": "",
        "Routes": [],
        "IpRanges": [],
        "ServerAuthorizationProperties": {
            "ServerAuthPropertiesHash": ""
        },
        "CamerasHash": "1627500085349",
        "Cameras": ["replace_me"],
        "StreamsHash": "1627501080053",
        "Streams": ["replace_me"],
        "RtmpSettings": {
            "hash": "1627501645916",
            "interfaces": [],
            "login": "",
            "password": "",
            "duration": 6,
            "chunk_count": 4,
            "dash_template": "TIME",
            "protocols": [
                "HLS",
                "DASH",
                "SLDP"
            ],
            "apps": [
                {
                    "app": "lowlatency",
                    "login": "",
                    "password": "",
                    "duration": 2,
                    "chunk_count": 10,
                    "jpg_thumbnails_interval": 2,
                    "jpg_thumbnail_width": 160,
                    "jpg_thumbnail_height": 90,
                    "dash_template": "TIME",
                    "protocols": [
                        "SLDP"
                    ]
                }
            ],
            "abr": []
        },
        "RtspSettings": {
            "hash": "1627500158161",
            "interfaces": []
        },
        "IcecastSettings": {
            "hash": "1627500160198",
            "interfaces": []
        },
        "LivePullSettings": {
            "hash": "1627500145995",
            "streams": []
        },
        "RtmpPublishSettings": {
            "hash": "",
            "settings": []
        },
        "RtspPublishSettings": {
            "hash": "",
            "settings": []
        },
        "ManagedTasks": {
            "hash": "0",
            "tasks": []
        },
        "HlsDRMSettings": {
            "hash": "0",
            "url": "",
            "key": "",
            "KeyServerSettings": {}
        },
        "HttpOriginApps": {
            "hash": "0",
            "apps": []
        },
        "Aliases": {
            "hash": "0",
            "settings": []
        },
        "DataSlicesInfo": {
            "hash": "1",
            "data_slices": [
                {
                    "id": "67497",
                    "tz": 0
                }
            ]
        },
        "UDPSenderSettings": {
            "hash": "0",
            "settings": []
        },
        "PayPerPublishSettings": {
            "hash": "0",
            "url": "",
            "auth_group_interval": 500,
            "apps": []
        },
        "DvrSettings": {
            "hash": "0",
            "settings": []
        },
        "UserAgentGroupSettings": {
            "hash": "0",
            "settings": []
        },
        "RefererGroupSettings": {
            "hash": "0",
            "settings": []
        },
        "VideoEncodersInfo": {
            "hash": "0",
            "encoders": []
        },
        "AudioEncodersInfo": {
            "hash": "0",
            "encoders": []
        },
        "StreamOverrideSettings": {
            "hash": "0",
            "settings": []
        },
        "IcecastStreamSettings": {
            "hash": "0",
            "settings": []
        },
        "AuthHandlerSettings": {
            "hash": ""
        },
        "ServerSettings": {
            "MaxCacheSize": 64,
            "MaxFileCacheSize": 4096,
            "LogMode": "info"
        }
    }
}

LOGGER.info("Beginning Camera and Streamer building...")
# Replace App Name
template_rules_conf_json['SyncResponse']['RtmpSettings']['apps'][0]['app'] = live_stream_app_name

# for each channel configure the lists for 'cameras' and 'streamers'
port_increment = 10
for channel_number in range(0,channel_count):

    for source_type in stream_source:
        if source_type == "emx":
            udp_start = udp_start_emx
            port_number = udp_start + port_increment
            stream_name = port_number
        else:
            udp_start = udp_start_emx + 1000
            port_number = udp_start + port_increment
            stream_name = port_number - 1000
        cameras = dict()
        cameras["id"] = "%03d-%s-%s" % (channel_number,port_number,"in")
        cameras["ip"] = "0.0.0.0"
        cameras["port"] = port_number # this is incrementing
        cameras["protocol"] = "udp"

        streams = dict()
        streams["id"] = "%03d%s" % (channel_number,"-out")
        streams["video"] = {}
        streams["video"]["cam"] = cameras['id'] # this reference camera ID
        streams["video"]["pid"] = 0
        streams["audio"] = {}
        streams["audio"]["cam"] = cameras['id'] # this reference camera ID
        streams["audio"]["pid"] = 0
        streams["app"] = source_type
        streams["stream"] = stream_name  # this is stream name and will be part of playback url

        cameras_list.append(cameras)
        streams_list.append(streams)
    port_increment += 10

# Replace Cameras List
template_rules_conf_json['SyncResponse']['Cameras'] = cameras_list
template_rules_conf_json['SyncResponse']['Streams'] = streams_list

LOGGER.info("Constructed New JSON")
LOGGER.info(template_rules_conf_json)

# write new json to nimble streamer location
# /etc/nimble/rules.conf
file = open("/etc/nimble/rules.conf","w")
file.write(json.dumps(template_rules_conf_json))
file.close()
