import boto3
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv
load_dotenv()

def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )

def create_bucket_with_options(bucket_name, versioning, tags=None, public_access_block=None, policy=None):
    s3 = get_s3_client()
    result = {}
    # Create bucket
    try:
        s3.create_bucket(Bucket=bucket_name)
        result['bucket_created'] = True
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            result['bucket_created'] = False
            result['message'] = 'Bucket already exists and is owned by you.'
        else:
            raise
    # Add tags
    if tags:
        s3.put_bucket_tagging(Bucket=bucket_name, Tagging={'TagSet': [{'Key': k, 'Value': v} for k, v in tags.items()]})
        result['tags_applied'] = True
    # Enable versioning
    if versioning:
        s3.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={'Status': 'Enabled'})
        result['versioning_enabled'] = True
    # Public access block
    if public_access_block:
        s3.put_public_access_block(Bucket=bucket_name, PublicAccessBlockConfiguration=public_access_block)
        result['public_access_block'] = public_access_block
    # Attach policy
    if policy:
        s3.put_bucket_policy(Bucket=bucket_name, Policy=policy)
        result['policy_attached'] = True
    return result

def apply_policy(bucket_name, policy_json):
    s3 = get_s3_client()
    s3.put_bucket_policy(Bucket=bucket_name, Policy=policy_json)
    return {'policy_applied': True}