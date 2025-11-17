from io import BytesIO

from botocore.response import StreamingBody
from fastapi.params import Depends
from pypdf import PdfReader, PdfWriter

from api import get_logger
from api.models.models import Book
from api.services.files import FilesService

LOG = get_logger(__name__)

class BookService:
    def __init__(self, files_service: FilesService = Depends()):
        self.files_service = files_service


    def parse_book(self, book: Book):
        LOG.info(f"Parsing book {book.id}")

        pdf_file = self.files_service.get_book_file(book)

        #  split it into individual page files
        pdf_pages = self._split_into_pages(pdf_file)

        # upload page files to the object store
        self.files_service.upload_book_pages(book, pdf_pages)

        #  split each page into sections,

        #  clean up text,
        #  convert into phonemes,
        #  store in DB.

    def _split_into_pages(self, pdf_file: StreamingBody):
        pdf_reader = PdfReader(BytesIO(pdf_file.read()))

        page_num = len(pdf_reader.pages)
        LOG.info("Number of pages: %s", page_num)

        pages = []
        for i in range(page_num):
            pdf_writer = PdfWriter()
            pdf_writer.add_page(pdf_reader.pages[i])
            current_page = {"file_name": f"{i}.pdf", "content": BytesIO()}
            pdf_writer.write(current_page["content"])
            current_page["content"].seek(0)
            pages.append(current_page)

        return pages
