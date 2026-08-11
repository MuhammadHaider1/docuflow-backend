from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from src.core.config import settings


class S3StorageManager:
    def __init__(self) -> None:
        self.session = aioboto3.Session()

    # 1. Return type ko Any set karein taake wrapper dynamic resolution chalaye
    def get_client(self) -> Any:
        protocol = "https" if settings.MINIO_SECURE else "http"
        complete_url = f"{protocol}://{settings.MINIO_ENDPOINT}"

        return self.session.client(
            "s3",
            endpoint_url=complete_url,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            use_ssl=settings.MINIO_SECURE,
        )

    async def initialize_bucket(self) -> None:
        """Application startup (lifespan) par bucket ensure karne ke liye"""
        # 2. Yahan context manager initialization line ke end par type ignore lagayein
        async with self.get_client() as s3:  # type: ignore
            try:
                await s3.head_bucket(Bucket=settings.MINIO_BUCKET_NAME)
                print(
                    f"📦 [MinIO] Bucket '{settings.MINIO_BUCKET_NAME}' already exists."
                )
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if error_code in ["404", "NoSuchBucket"]:
                    print(
                        f"🚀 [MinIO] Bucket '{settings.MINIO_BUCKET_NAME}' not found. Creating..."
                    )
                    await s3.create_bucket(Bucket=settings.MINIO_BUCKET_NAME)
                    print(
                        f"✅ [MinIO] Bucket '{settings.MINIO_BUCKET_NAME}' successfully created!"
                    )
                else:
                    raise e


storage_manager = S3StorageManager()
