import json
import boto3

# boto3 S3 initialization
s3_client = boto3.client("s3")


def lambda_handler(event, context):
    # event contains all information about uploaded object
    print("Event :", event)
    
    # Bucket Name where file was uploaded
    bucket_name = event['Records'][0]['s3']['bucket']['name']

    # Filename of object (with path)
    file_key_name = event['Records'][0]['s3']['object']['key']
    
    # New Filename
    new_key_name = file_key_name.replace(file_key_name.rsplit('/',1)[1] , file_key_name.rsplit('/',1)[1].split('.')[0]+'.jpg' )
    print("INFO : new key name: ",new_key_name)
    print("INFO : copying object from : ",bucket_name,file_key_name)
    
    # Copy Source Object
    copy_source_object = {'Bucket': bucket_name, 'Key': file_key_name}

    # S3 copy object operation
    s3_client.copy_object(CopySource=copy_source_object, Bucket=bucket_name, Key=new_key_name, ACL='public-read')
    
    # S3 delete original object
    s3_client.delete_object(Bucket=bucket_name,Key=file_key_name)
    
    print("Done")
    return "finished"
