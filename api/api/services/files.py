import logging
import os
import uuid

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from api.models.models import TempFile


class FilesService:
    """A service to manage files stored in an object store."""

    def __init__(self):
        load_dotenv()
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT"),
            aws_access_key_id=os.getenv("S3_ACCESS"),
            aws_secret_access_key=os.getenv("S3_SECRET")
        )
        self.bucket_name = os.getenv("S3_BUCKET", "narrator")

    def store_book_file(self, book_id: uuid.UUID, book_file: TempFile):
        """Move the book file from the local disk to the object store."""
        remote_file_path = f"{book_id}/{book_file.file_name}"

        try:
            self.s3_client.upload_file(book_file.file_path, self.bucket_name, remote_file_path)
        except ClientError as e:
            logging.error(e)
            raise e
