import boto3
import botocore.exceptions
from app.core.config import settings

def get_s3_client():
    """Returns a configured boto3 client for S3/Minio."""
    client = boto3.client(
        's3',
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name="us-east-1"  # Minio often requires a region, even a dummy one
    )
    return client

def ensure_bucket_exists():
    """Ensure the target bucket exists in Minio/S3."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
    except botocore.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
        else:
            raise

def upload_file_to_s3(local_path: str, object_name: str) -> str:
    """Uploads a local file to S3 and returns the S3 URI/Key."""
    client = get_s3_client()
    client.upload_file(local_path, settings.S3_BUCKET_NAME, object_name)
    return f"s3://{settings.S3_BUCKET_NAME}/{object_name}"

def upload_fileobj_to_s3(file_obj, object_name: str) -> str:
    """Uploads a file-like object to S3 and returns the S3 URI."""
    client = get_s3_client()
    client.upload_fileobj(file_obj, settings.S3_BUCKET_NAME, object_name)
    return f"s3://{settings.S3_BUCKET_NAME}/{object_name}"

def download_file_from_s3(object_name: str, local_path: str):
    """Downloads a file from S3 to a local path."""
    client = get_s3_client()
    client.download_file(settings.S3_BUCKET_NAME, object_name, local_path)

def get_file_content_from_s3(object_name: str) -> bytes:
    """Gets the content of a file directly from S3."""
    client = get_s3_client()
    response = client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=object_name)
    return response['Body'].read()

def generate_presigned_url(object_name: str, expiration=3600) -> str:
    """Generates a pre-signed URL to download or stream a file."""
    client = get_s3_client()
    response = client.generate_presigned_url(
        'get_object',
        Params={'Bucket': settings.S3_BUCKET_NAME, 'Key': object_name},
        ExpiresIn=expiration
    )
    return response

# On import, make sure bucket exists
ensure_bucket_exists()
