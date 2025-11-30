# studio/s3_utils.py

import uuid
from pathlib import Path
import boto3

S3_BUCKET = "gifpt-s3"          # 네가 만든 버킷 이름
S3_REGION = "ap-northeast-2"        # seoul이면 이거

s3 = boto3.client("s3", region_name=S3_REGION)

def upload_to_s3(local_path: str) -> str:
    """
    로컬 mp4 파일을 S3에 업로드하고, 접근 가능한 URL을 리턴.
    버킷 권한에 따라 public URL / presigned URL 중 택1.
    """
    suffix = Path(local_path).suffix or ".mp4"
    key = f"videos/{uuid.uuid4()}{suffix}"

    s3.upload_file(
        local_path,
        S3_BUCKET,
        key,
        ExtraArgs={
            "ContentType": "video/mp4",
            # public 버킷이면:
            "ACL": "public-read",
        }
    )

    # 퍼블릭 버킷 기준 URL
    return f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"