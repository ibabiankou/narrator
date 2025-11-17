import os
import uuid

import boto3
from dotenv import load_dotenv

from api.models.models import TempFile


class FilesService:
    """A service to manage files stored in an object store."""

    def __init__(self):
        load_dotenv()
        s3_client = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT"),
            aws_access_key_id=os.getenv("S3_ACCESS"),
            aws_secret_access_key=os.getenv("S3_SECRET")
        )
        print("Hello, Amazon S3! Let's list your buckets:")

        # Create a paginator for the list_buckets operation.
        paginator = s3_client.get_paginator("list_buckets")

        # Use the paginator to get a list of all buckets.
        response_iterator = paginator.paginate(
            PaginationConfig={
                "PageSize": 50,  # Adjust PageSize as needed.
                "StartingToken": None,
            }
        )

        # Iterate through the pages of the response.
        buckets_found = False
        for page in response_iterator:
            if "Buckets" in page and page["Buckets"]:
                buckets_found = True
                for bucket in page["Buckets"]:
                    print(f"\t{bucket['Name']}")

        if not buckets_found:
            print("No buckets found!")

    def store_book_file(self, book_id: uuid.UUID, book_file: TempFile):
        """Move the book file from the local disk to the object store."""
        pass
