from io import BytesIO

from botocore.response import StreamingBody
from fastapi.params import Depends
from pypdf import PdfReader, PdfWriter

from api import get_logger, get_session
from api.models.models import Book, Section, DbSession
from api.services.files import FilesService

LOG = get_logger(__name__)


class BookService:
    def __init__(self, files_service: FilesService = Depends()):
        self.files_service = files_service

    def parse_book(self, book: Book):
        LOG.info(f"Parsing book {book.id}")

        pdf_file = self.files_service.get_book_file(book)

        # Split it into individual page files
        pdf_pages = self._split_into_pages(pdf_file)

        # Upload page files to the object store
        self.files_service.upload_book_pages(book, pdf_pages)

        # Split each page into sections. A section is one or more paragraphs.
        section_dicts = self._split_into_sections(pdf_file)

        # TODO: clean up text,
        # TODO: convert into phonemes,

        # Persist Sections in DB.
        sections = []
        for section_index in range(len(section_dicts)):
            section_dict = section_dicts[section_index]
            section = Section(book_id=book.id,
                              page_index=section_dict["page_index"],
                              section_index=section_index,
                              content=section_dict["content"])
            sections.append(section)

        with DbSession() as session:
            session.add_all(sections)
            session.commit()

    def _split_into_pages(self, pdf_file: BytesIO):
        pdf_file.seek(0)
        pdf_reader = PdfReader(pdf_file)

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

    def _split_into_sections(self, pdf_file: BytesIO):
        pdf_file.seek(0)
        pdf_reader = PdfReader(pdf_file)

        sections = []

        page_num = len(pdf_reader.pages)
        for page_index in range(page_num):
            page = pdf_reader.pages[page_index]
            text = self._remove_key_words(page.extract_text())
            lines = text.splitlines()
            for line in lines:
                sections.append({
                    "page_index": page_index,
                    "content": line
                })

        return sections

    def _remove_key_words(self, text: str) -> str:
        # TODO: extract the list of key words to some kind of config...
        key_words = ["OceanofPDF.com", "OceanofPDF .com"]
        for key_word in key_words:
            text = text.replace(key_word, "\n")
        return text
