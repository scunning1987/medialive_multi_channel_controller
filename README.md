# MediaLive Channel Controller

## Overview

This is a solution designed for companies or individuals that have a need to do accurate source switching on their live event channels. The full-features MediaLive Scheduling API/SDK makes this possible. Other core AWS services have been used to create a very robust and lightweight solution.

## Architecture

placeholder

## How To Deploy

Deploy using [this CloudFormation template](./medialive_multi_channel_controller-public.yaml)

[comment]: <> (## Architecture)

[comment]: <> (![]&#40;images/workflow-with-lowlatency-preview-arc.png?width=60pc&classes=border,shadow&#41;)

[comment]: <> (This solution has been designed to deploy around an existing video pipeline. The architecture drawing shows a fully redundant video pipeline that utilizes the MediaLive Controller solution to enrich the live stream experience.)

[comment]: <> (If you are wanting to deploy an entire solution from scratch, here are the steps:)

[comment]: <> (1. Deploy your video pipeline.. This readme doesn't contain instructions for that. Check out [this blog post]&#40;https://aws.amazon.com/blogs/media/awse-quickly-creat-live-streaming-channel-aws-elemental-medialive-workflow-wizard/&#41; that features the *Workflow Wizard*, a Media Services tool used to deploy all required components)

[comment]: <> (2. Deploy this *MediaLive Controller* solution, by using the CloudFormation template provided below. The services used include Amazon CloudFront, Amazon S3, Amazon API Gateway, AWS Lambda)

[comment]: <> (3. Deploy a couple of EC2 instances to act as *low latency streamers* for the MediaLive Controller solution)

[comment]: <> (4. Configure your MediaLive channels to send proxy streams to the EC2 instances)

[comment]: <> (5. Configure CloudFront to serve the low latency stream from your EC2 instances, an origin group is recommended)

[comment]: <> (6. Add AWS WAF as a layer of security)

[comment]: <> (## How To Deploy)

[comment]: <> (### Deploy your video pipeline)

[comment]: <> (As mentioned above, this guide doesn't contain instructions for that. Go to the blog post mentioned for easy deployment, or pick an existing video pipeline to add this solution to)

[comment]: <> (### Deploy the MediaLive Controller)

[comment]: <> (This solution is deployed via CloudFormation, it utilizes the following services:)

[comment]: <> (- AWS IAM)

[comment]: <> (- AWS Lambda)

[comment]: <> (- Amazon API Gateway)

[comment]: <> (- Amazon CloudFront)

[comment]: <> (- Amazon S3)

[comment]: <> (1. Download the CloudFormation template [here]&#40;./medialive_multi_channel_controller.yaml&#41;)

[comment]: <> (2. Login to the AWS Console and open the CloudFormation service console)

[comment]: <> (3. Select the **Create stack** button, then select *with new resources*)

[comment]: <> (4. In step 1 of the create stack wizard, select *Upload a template file*, then browse to the CloudFormation template you downloaded, then select Next)

[comment]: <> (5. Give the stack a name. Some of the services that deploy may use this name when creating resources. Most services will use this name as a Tag identifier.)

[comment]: <> (6. Provide a valid S3 policy for an S3 bucket that contains media to be used in this workflow. You can leave the default value if you like, this will just allow the solution to READ from any S3 bucket in the account. Select Next)

[comment]: <> (7. All options on this page are optional, please look through them and only use if necessary. Select Next)

[comment]: <> (8. This is the review page outlining summary of the wizard. At the bottom there is a checkbox that you have to acknowledge. This is specifying that the CloudFormation stack will make IAM changes; an IAM role is created, and an IAM policy is attached to it. This is necessary for Lambda to perform the necessary control functions on the MediaLive channel&#40;s&#41;)

[comment]: <> (9. Select **Create stack**)

