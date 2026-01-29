import logging
import mimetypes
import os
import uuid
from dataclasses import dataclass
from typing import Annotated, Optional, List

import boto3
from botocore.exceptions import ClientError

from api import get_logger
from api.models import db
from api.models.db import DbSession
from common_lib.service import Service

LOG = get_logger(__name__)


@dataclass
class FileData:
    body: bytes
    content_type: str
    etag: str
    range: Optional[str]


class NotModified(Exception):
    pass


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

    def store_book_file(self, book_id: uuid.UUID, book_file_id: uuid.UUID):
        """Move the book file from the local disk to the object store."""
        with DbSession() as session:
            book_file = session.get_one(db.TempFile, book_file_id)

            remote_file_path = f"{book_id}/{book_file.file_name}"
            LOG.info(f"Uploading {remote_file_path}")

            try:
                self.s3_client.upload_file(book_file.file_path, self.bucket_name, remote_file_path)
            except ClientError as e:
                logging.error(e)
                raise e
            return book_file.file_name

    def upload_book_pages(self, book_id: uuid.UUID, pdf_pages):
        """Upload the book pages to the object store."""

        pages_dir_path = f"{book_id}/pages"
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

    def _get_object(self, key: str, if_none_match: Optional[str] = "", range: Optional[str] = "bytes=0-") -> Optional[
        FileData]:
        try:
            s3_object = self.s3_client.get_object(Bucket=self.bucket_name,
                                                  Key=key,
                                                  IfNoneMatch=if_none_match,
                                                  Range=range)
            return FileData(body=s3_object["Body"].read(),
                            content_type=s3_object["ContentType"],
                            etag=s3_object["ETag"],
                            range=s3_object.get("ContentRange"))
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "NoSuchKey":
                return None
            elif code == "304":
                raise NotModified()
            else:
                raise e

    @staticmethod
    def speech_filename(book_id: uuid.UUID, file_name: str = ""):
        if file_name:
            return f"{book_id}/speech/{file_name}"
        else:
            return f"{book_id}/speech"

    def delete_speech_file(self, book_id: uuid.UUID, file_name: str):
        remote_file_path = self.speech_filename(book_id, file_name)
        self.delete_file(remote_file_path)

    def delete_file(self, key: str):
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key)
        except ClientError as e:
            logging.error(e)
            raise e

    def list_files(self, path_prefix: str) -> List[str]:
        paginator = self.s3_client.get_paginator('list_objects_v2')

        keys = []
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=path_prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    keys.append(obj["Key"])

        return keys

    def _delete_objects(self, keys: list[str]):
        for i in range(0, len(keys), 500):
            chunk = keys[i:i + 500]
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={
                    "Objects": [
                        {"Key": key}
                        for key in chunk
                    ]
                }
            )

    def delete_book_files(self, book_id):
        keys = self.list_files(f"{book_id}/")
        LOG.info("Deleting %s files \n%s", len(keys), keys)
        if keys:
            self._delete_objects(keys)

    def exists(self, file_key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            else:
                raise e

    def list_dirs(self, prefix: str, delimiter: str = '/') -> List[str]:
        result = []
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix, Delimiter=delimiter)
        if 'CommonPrefixes' in response:
            for pre in response['CommonPrefixes']:
                # Remove trailing delimiter
                parts = pre['Prefix'].rsplit(delimiter, 1)
                result.append("".join(parts))
        return result

FilesServiceDep = Annotated[FilesService, FilesService.dep()]
