"""
Cloudflare R2 client — S3-compatible object storage for uploaded CSV files.

Usage:
    from app.utils.r2_client import r2_client

    # Upload
    key = r2_client.upload("uploads/job-id_file.csv", raw_bytes)

    # Download
    buffer = r2_client.download("uploads/job-id_file.csv")
    df = pd.read_csv(buffer)

    # Delete (after processing)
    r2_client.delete("uploads/job-id_file.csv")

If R2 credentials are not configured, all methods return None and log a warning.
The endpoint falls back to local disk storage in that case.
"""
import io
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class R2Client:
    """
    Thin wrapper around boto3 configured for Cloudflare R2.
    R2 is S3-compatible so boto3 works with a custom endpoint_url.
    """

    def __init__(self):
        self._client = None
        self._bucket: Optional[str] = None

        if not settings.R2_CONFIGURED:
            logger.info(
                "Cloudflare R2 not configured — CSV files will be stored on local disk. "
                "Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, "
                "and R2_BUCKET_NAME to enable R2 storage."
            )
            return

        try:
            import boto3
            self._client = boto3.client(
                "s3",
                endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name="auto",   # R2 requires "auto" as region
            )
            self._bucket = settings.R2_BUCKET_NAME
            logger.info(f"Cloudflare R2 client initialised. Bucket: {self._bucket}")
        except Exception as e:
            logger.error(f"Failed to initialise R2 client: {e}")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def upload(self, key: str, data: bytes) -> str:
        """
        Upload raw bytes to R2.
        Returns the object key on success, raises on failure.
        """
        if not self._client:
            raise RuntimeError("R2 client is not configured.")
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)
        logger.info(f"R2 upload: s3://{self._bucket}/{key} ({len(data)} bytes)")
        return key

    def download(self, key: str) -> io.BytesIO:
        """
        Download an object from R2.
        Returns a BytesIO buffer ready to be passed to pandas.
        """
        if not self._client:
            raise RuntimeError("R2 client is not configured.")
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        buffer = io.BytesIO(response["Body"].read())
        logger.info(f"R2 download: s3://{self._bucket}/{key}")
        return buffer

    def delete(self, key: str) -> None:
        """Delete an object from R2 after processing."""
        if not self._client:
            return
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            logger.info(f"R2 delete: s3://{self._bucket}/{key}")
        except Exception as e:
            # Non-fatal — log and continue (job is already complete)
            logger.warning(f"R2 delete failed for {key}: {e}")


# Singleton — shared across the process
r2_client = R2Client()
