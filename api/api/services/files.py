import logging
import os
import uuid
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from dotenv import load_dotenv

from api import get_logger
from api.models.models import TempFile, Book

LOG = get_logger(__name__)

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

    def get_book_file(self, book: Book) -> BytesIO:
        """Get the book file from the object store."""
        remote_file_path = f"{book.id}/{book.file_name}"
        pdf_object = self.s3_client.get_object(Bucket=self.bucket_name, Key=remote_file_path)
        return BytesIO(pdf_object["Body"].read())

    def upload_book_pages(self, book: Book, pdf_pages):
        """Upload the book pages to the object store."""

        pages_dir_path = f"{book.id}/pages"
        for page in pdf_pages:
            page_file_name = page["file_name"]
            remote_path = f"{pages_dir_path}/{page_file_name}"
            LOG.info(f"Uploading {remote_path}")

            self.s3_client.put_object(
                Body=page["content"],
                Bucket=self.bucket_name,
                Key=remote_path)
