import logging
import mimetypes
import os
import uuid
from io import BytesIO
from typing import Annotated

import boto3
from botocore.exceptions import ClientError

from api import get_logger
from api.models.db import TempFile, Book
from common_lib.service import Service

LOG = get_logger(__name__)
boto3.set_stream_logger('botocore.endpoint', logging.DEBUG)
boto3.set_stream_logger('botocore.parsers', logging.DEBUG)
boto3.set_stream_logger('botocore.retryhandler', logging.DEBUG)


class FilesService(Service):
    """A service to manage files stored in an object store."""

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT"),
            region_name=os.getenv("S3_REGION"),
            aws_access_key_id=os.getenv("S3_ACCESS"),
            aws_secret_access_key=os.getenv("S3_SECRET")
        )
        self.bucket_name = os.getenv("S3_BUCKET", "narrator")

    def store_book_file(self, book_id: uuid.UUID, book_file: TempFile):
        """Move the book file from the local disk to the object store."""
        remote_file_path = f"{book_id}/{book_file.file_name}"
        LOG.info(f"Uploading {remote_file_path}")

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

            mime_type, encoding = mimetypes.guess_type(remote_path)
            self.s3_client.put_object(
                Body=page["content"],
                Bucket=self.bucket_name,
                Key=remote_path,
                ContentType=mime_type)

    def get_book_page_file(self, book_id: uuid.UUID, page_file_name: str) -> dict | None:
        """Get the book page file from the object store."""
        return self._get_object(f"{book_id}/pages/{page_file_name}")


    def _get_object(self, key: str) -> dict | None:
        try:
            s3_object = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return {
                "body": s3_object["Body"].read(),
                "content_type": s3_object["ContentType"]
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            else:
                raise e

    def store_speech_file(self, book_id: uuid.UUID, file_name: str, speech_data: bytes):
        """Store speech data to the object store."""
        remote_file_path = self.speech_filename(book_id, file_name)

        try:
            mime_type, encoding = mimetypes.guess_type(remote_file_path)
            self.s3_client.put_object(
                Body=speech_data,
                Bucket=self.bucket_name,
                Key=remote_file_path,
                ContentType=mime_type)
        except ClientError as e:
            logging.error(e)
            raise e

    def speech_filename(self, book_id: uuid.UUID, file_name: str):
        return f"{book_id}/speech/{file_name}"

    def get_speech_file(self, book_id: uuid.UUID, file_name: str) -> dict | None:
        """Get the speech file from the object store."""
        return self._get_object(self.speech_filename(book_id, file_name))

    def delete_speech_file(self, book_id: uuid.UUID, file_name: str):
        remote_file_path = self.speech_filename(book_id, file_name)

        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=remote_file_path)
        except ClientError as e:
            logging.error(e)
            raise e

FilesServiceDep = Annotated[FilesService, FilesService.dep()]
