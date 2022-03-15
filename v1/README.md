# MediaLive Multi-Channel Controller
## Summary
This solution was designed to provide universal operation of multiple MediaLive channels. Offering real-time visibility into the channel state, allowing for channel controls, and confidence monitoring of the channel outputs. The AWS services utilized in this process besides AWS Elemental MediaLive, include Amazon API Gateway, AWS Lambda, Amazon S3, Amazon CloudWatch.

The solution consists of 3 workflows that need to be configured to work in unison. The first workflow requires an Amazon S3 bucket, and then involves the creation of a MediaLive channel with an ABR output as well as a “Frame Capture to JPG” output, writing to the S3 bucket. Lastly, an AWS Lambda function is required to perform JPG name rewrites for every PUT action performed by MediaLive. This is because MediaLive increments the naming of the JPG’s it writes to S3, which is not suitable for an HTML monitoring page that expects a static JPG URL to GET.

The second workflow is the deployment of the HTML control page. This requires an Amazon S3 bucket (which can be the same as the bucket used in workflow 1). Then an AWS Lambda function and API Gateway endpoint must be created to perform control actions on the services.

The last part of the workflow involves the use of overwriting channel JPG’s to show the operator the current channel state. A CloudWatch event rule must be setup to trigger a Lambda function that will read the event detail, then write the corresponding JPG to the channel status JPG name

Note that the solution supports MediaLive channels in multiple regions. However, in order for the solution to work correctly, each region that a MediaLive channel has been deployed into needs to have a CloudWatch event rule and AWS Lambda deployed.

![](images/dashboard-sample.png?width=60pc&classes=border,shadow)

## Architecture Overview
### High Level
![](images/Architecture_001.png?width=60pc&classes=border,shadow)

### MediaLive JPG Rename
This part of the workflow focuses on MediaLive, Amazon S3, CloudWatch, and AWS Lambda. The goal is to rename incrementing namings of MediaLive JPG outputs to a predictable static name...

1. MediaLive channel contains multiple outputs, one of which is required to be the "Frame Capture to JPEG" for use with the MediaLive Controller UI. MediaLive creates thumbnails at pre-defined intervals and PUT's them on S3. MediaLive increments the suffix of the filename for every PUT. 
2. An S3 PUT event trigger invokes a Lambda function to run 
3. The Lambda copies the filename of the JPG that was just uploaded (ie. status000001.jpg) to a pre-defined location for the channel status jpg (ie. s3://cunsco/medialive/channel1/status.jpg). Lambda then deletes the originally uploaded file.

![](images/Architecture_002.png?width=60pc&classes=border,shadow)

### Operation and Control Functions
This part of the workflow focuses on the operator UI on S3, Amazon API Gateway, AWS Lambda, Amazon CloudWatch and MediaLive. The MediaLive channels need to be created (and optionally MediaPackage, CloudFront optional), the MediaLive controller Lambda function, and Amazon API Gateway endpoint must be deployed. Lastly, the Javascript file for the operator UI needs to be edited, then deployed in Amazon S3 with the HTML, CSS, and other channel state JPG's (starting, stopped, stopping)

![](images/Architecture_003.png?width=60pc&classes=border,shadow)

### Channel State Change "JPG" Updates
MediaLive takes time to start and stop, usually up to 2 minutes.. Operators like to see feedback almost instantly after performing actions such as starting and stopping channels. To solve this problem, a CloudWatch event rule needs to be setup to capture these channel event types, and invoke a Lambda to replace the channel's 'status.jpg' with a static channel state jpg. This channel state jpg will them remain on S3 until the channel is in a running state and starts overwriting the S3 status.jpg

![](images/Architecture_004.png?width=60pc&classes=border,shadow)

## Limitations, Restrictions, and Assumptions
* MediaLive channels must have at least 1 static input and at least 1 dynamic MP4 input (see details in MediaLive section). It is preferred to have 2 dynamice MP4 inputs (one set to LOOP, one set to CONTINUE behavior)
* AWS Lambda must be able to change ACL on files to 'public-read'. If this violates your security protocols, you can remove this option from the Lambda functions (MediaLiveJPGRenamer) and need to deploy a CloudFront distribution to serve the Controller UI and JPG's publicly
* S3 bucket(s)  Block all public access must be off. If this is a security concern, you can optionally deploy a CloudFront distribution to serve the MediaLive controller UI and JPG's from CloudFront
* If CloudFront is used, disable caching (using behavior policies). No instructions are provided in this solution for CloudFront
* The channel preview player only works with unencrypted HLS
* The channel preview player is videoJS

## AWS Services
The AWS Services used for this workflow:

* IAM 
* AWS Lambda
* Amazon API Gateway
* Amazon CloudWatch
* AWS Elemental MediaPackage 
* AWS Elemental MediaLive
* Amazon S3
* Amazon WAF (Web Application Firewall)

## Deployment Instructions
### CloudFormation
**Coming Really Soon**

### Required MediaLive channel Configuration
#### Thumbnail Output
Required for multiviewer style viewing of the stream

*instructions coming soon*

#### HLS Output
*Output to MediaPackage, MediaStore, or other is acceptable, we just need to know the master m3u8

### Submitting Channel Config to the system
The solution has a custom API listening for channel configuration updates. This config then gets pushed to the system and the HTML page is updated with the new channnel layout. A refresh is required

#### Example API call with POST data

*Coming soon*