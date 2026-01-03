import logging
import mimetypes
import os
import uuid
from dataclasses import dataclass
from io import BytesIO
from typing import Annotated, Optional

import boto3
from botocore.exceptions import ClientError

from api import get_logger
from api.models.db import TempFile, Book
from common_lib.service import Service

LOG = get_logger(__name__)


@dataclass
class FileData:
    body: bytes
    content_type: str
    etag: str

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

    def get_book_page_file(self,
                           book_id: uuid.UUID,
                           page_file_name: str,
                           if_none_match: Optional[str] = None) -> Optional[FileData]:
        """Get the book page file from the object store."""
        return self._get_object(f"{book_id}/pages/{page_file_name}")


    def _get_object(self, key: str, if_none_match: Optional[str] = None) -> Optional[FileData]:
        try:
            s3_object = self.s3_client.get_object(Bucket=self.bucket_name,
                                                  Key=key,
                                                  IfNoneMatch=if_none_match or "fake-value")
            return FileData(body=s3_object["Body"].read(),
                            content_type=s3_object["ContentType"],
                            etag=s3_object["ETag"])
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            else:
                raise e

    def speech_filename(self, book_id: uuid.UUID, file_name: str):
        return f"{book_id}/speech/{file_name}"

    def get_speech_file(self,
                        book_id: uuid.UUID,
                        file_name: str,
                        if_none_match: Optional[str] = None) -> Optional[FileData]:
        """Get the speech file from the object store."""
        return self._get_object(self.speech_filename(book_id, file_name), if_none_match)

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
