import uuid
from io import BytesIO
from typing import Annotated

import pymupdf
from pypdf import PdfReader, PdfWriter
from sqlalchemy import update

from api import get_logger
from api.models.db import Book, Section, DbSession, BookStatus
from api.services.files import FilesServiceDep
from api.utils.text import ParagraphBuilder, SectionBuilder, LineReader, CleanupPipeline
from common_lib.service import Service

LOG = get_logger(__name__)


class BookService(Service):
    def __init__(self, files_service: FilesServiceDep):
        self.files_service = files_service

    def split_pages(self, book: Book):
        LOG.debug(f"Splitting book {book.id} into pages.")

        pdf_file = self.files_service.get_book_file(book)

        # Split it into individual page files
        pdf_pages = self._split_into_pages(pdf_file)

        # Upload page files to the object store
        self.files_service.upload_book_pages(book, pdf_pages)

    def get_text(self, book: Book, first_page: int = None, last_page: int = None, raw: bool = False):
        pdf_bytes = self.files_service.get_book_file(book)
        doc = pymupdf.open(stream=pdf_bytes, filetype="application/pdf")
        pages = [p.get_text() for p in doc]

        line_reader = LineReader(pages, CleanupPipeline([] if raw else CleanupPipeline.ALL_TRANSFORMERS))
        lines = []
        while line_reader.has_next():
            page_index, line = line_reader.next()

            if first_page is not None and page_index < first_page:
                continue
            if last_page is not None and page_index > last_page:
                break

            lines.append(line)

        return "\n".join(lines)

    def extract_text(self, book: Book):
        LOG.info(f"Extracting text of the book {book.id}")

        # Split each page into sections. A section is one or more paragraphs.
        pdf_bytes = self.files_service.get_book_file(book)

        doc = pymupdf.open(stream=pdf_bytes, filetype="application/pdf")
        pages = [p.get_text() for p in doc]
        page_num = len(pages)
        section_dicts = split_into_sections(pages)

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
            session.execute(
                update(Book).where(Book.id == book.id).values(status=BookStatus.ready, number_of_pages=page_num))
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

    def get_book(self, book_id: uuid.UUID):
        with DbSession() as session:
            return session.get_one(Book, book_id)

def split_into_sections(pages: list[str]):
    sections = []
    line_reader = LineReader(pages, CleanupPipeline(CleanupPipeline.ALL_TRANSFORMERS))
    while line_reader.has_next():
        section_builder = SectionBuilder()
        while section_builder.need_more_text() and line_reader.has_next():
            paragraph_builder = ParagraphBuilder()
            while paragraph_builder.need_more_text() and line_reader.has_next():
                paragraph_builder.append(line_reader.next())

            if (section_builder.page_index is not None
                    and paragraph_builder.page_index != section_builder.page_index
                    and not section_builder.is_empty()
            ):
                sections.append(section_builder.build())
                section_builder = SectionBuilder()

            section_builder.append(paragraph_builder.build())

        sections.append(section_builder.build())

    return sections

BookServiceDep = Annotated[BookService, BookService.dep()]
