# studio/s3_utils.py

import uuid
from pathlib import Path
import boto3

S3_BUCKET = "gifpt-demo"          # 네가 만든 버킷 이름
S3_REGION = "us-east-1"        # seoul이면 이거

s3 = boto3.client("s3", region_name=S3_REGION)

def upload_to_s3(file_path: str) -> str:
    s3 = boto3.client("s3")
    bucket = "gifpt-demo"
    key = f"videos/{uuid.uuid4()}.mp4"

    # ✅ ACL 제거, ContentType 정도만 유지
    s3.upload_file(
        file_path,
        bucket,
        key,
        ExtraArgs={
            "ContentType": "video/mp4"
        }
    )

    # presigned URL 쓰거나, CloudFront/S3 도메인 조합해서 URL 반환
    return f"https://{bucket}.s3.amazonaws.com/{key}"
    