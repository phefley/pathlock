import os
import json
import boto3
from botocore.exceptions import ClientError


DEBUG = False
PATHKEY = ['insert','your','key','here']
TABLENAME = 'INSERT' # dynamodb table name
SGID = 'sg-STUFF' # security group ID to modify on win 
DESTPORT = 22 # port to open in the security group
KEYFILE_NAME = 'OBJECT' # the object name to give access to in the S3 bucket on win
KEYFILE_BUCKET = 'BUCKET' # a bucket name to pull static files from 
BASEURL = 'https://something.something.net' # the base URL for this function


def create_presigned_url(bucket_name, object_name, expiration=3600):
    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': object_name}, ExpiresIn=expiration)
    except ClientError as e:
        print(e)
        return None
    return response


def hasAccessTo(cidrAddressStr, portNumberInt):
    print("Checking access for", cidrAddressStr, "to", portNumberInt)
    ec2Client = boto3.client('ec2')
    retval = False
    response = ec2Client.describe_security_group_rules(Filters=[{'Name':'group-id','Values':[SGID]}])
    for rule in response['SecurityGroupRules']:
        if rule['FromPort']==portNumberInt and rule ['ToPort']==portNumberInt and rule['CidrIpv4']==cidrAddressStr:
            retval = True
            break
    return retval


def grantAccessToTcpPort(sourceCidrStr, portNumberInt):
    ec2Client = boto3.client('ec2')
    response = ec2Client.authorize_security_group_ingress(GroupId=SGID,IpProtocol="tcp",FromPort=portNumberInt,ToPort=portNumberInt,CidrIp=sourceCidrStr)


def lambda_handler(event, context):
    client = boto3.client('dynamodb')
    currentCallerPosition = 0
    tableEntryExists = False
    
    pathType = None
    if 'rawPath' in event.keys():
        path = event['rawPath']
        pathType = 'raw'
    elif 'path' in event.keys():
        path = event['path']
        pathType = 'event'
    else:
        path = ''
        
    sourceIp = None
    if 'requestContext' in event.keys():
        if 'http' in event['requestContext'].keys():
            if 'path' in event['requestContext']['http'].keys():
                path = event['requestContext']['http']['path']
                pathType = 'context'
        
            
        if 'identity' in event['requestContext'].keys():
            if 'sourceIp' in event['requestContext']['identity'].keys():
                sourceIp = event['requestContext']['identity']['sourceIp']
    
    # If the path is empty or "/", return the dummy page.
    if path != '' and path != '/':
        # Process the pathlock
        dirs = path.split('/')[1:] # The first / will need to be cut off
        if dirs[0] in PATHKEY:
            # This will indicate that we actually need to do something:
            GetItem = client.get_item(
                TableName=TABLENAME,
                Key={
                    'source': {
                      'S': sourceIp
                    }
                }
            )
            if 'Item' in GetItem.keys():
                #This only happens if the record exists.
                currentCallerPosition = int(GetItem['Item']['position']['N'])
                print(">> CallerPosition: ",currentCallerPosition)
                tableEntryExists = True
        
            for dir in dirs:
                if dir == PATHKEY[currentCallerPosition]:
                    currentCallerPosition += 1
                    if currentCallerPosition == len(PATHKEY):
                        # We don't need to keep testing, they won!
                        # Grant them access:
                        keyUrl = create_presigned_url(KEYFILE_BUCKET,KEYFILE_NAME,300)
                        if not hasAccessTo(sourceIp + "/32",DESTPORT):
                            grantAccessToTcpPort(sourceIp + "/32",DESTPORT)
                        # If the entry exists, let's reset their position
                        if tableEntryExists:
                            DeleteItem = client.delete_item(TableName=TABLENAME,Key={'source':{'S':sourceIp}})
                        return {
                            "statusCode" : 200,
                            "headers" : {
                                "Content-Type": "application/json"
                            },
                            "body": json.dumps({
                                "win":"True",
                                "key":keyUrl,
                                "source":sourceIp
                            })
                        }
                else:
                    break # This assumes no prepended junk dirs
        
            # Update the caller's record
            PutItem = client.put_item(
                TableName=TABLENAME,
                Item={
                    'source': {
                        'S': sourceIp
                    },
                    'position': {
                        'N': str(currentCallerPosition)
                    }
                }
            )
    
    if DEBUG:
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "test":"valid",
                "path":path,
                "source":sourceIp
            })
        }
    else:
        return {
            "statusCode": 302,
            "headers": {
                "Location": BASEURL + "/index.html",
                "Content-Type": "text/html"
            },
            "body": ""            
        }

