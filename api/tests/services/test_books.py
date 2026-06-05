import os
import pytest
import uuid
from io import BytesIO

from api.services.books import BookService

books_service = BookService(None, None, None, None, None)


class TestBooksService:
    @pytest.mark.skip(reason="Requires a file to present. To be deleted later")
    def test_extract_images(self):
        pdf_file_path = "/Users/ibabiankou/Downloads/_OceanofPDF.com_Awakening_-_Sarah_Hawke.pdf"
        pdf_bytes = BytesIO(open(pdf_file_path, "rb").read())
        book_id = uuid.UUID("84efd0c9-80b5-46f4-bf13-44b3726baf25")

        images = books_service._extract_images(book_id, pdf_bytes)

        for image in images:
            file_path = f"/Users/ibabiankou/repos/narrator/out/{image['file_name']}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "wb") as fp:
                fp.write(image["content"].read())

            print(f"Saved: {file_path}")

    def test_master_playlist(self):
        id = uuid.UUID("84efd0c9-80b5-46f4-bf13-44b3726baf25")

        playlist = books_service._generate_master_playlist(id, "kokoro", "am_michael")
        print()
        print(playlist)
