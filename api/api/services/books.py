from io import BytesIO

from fastapi.params import Depends
from pypdf import PdfReader, PdfWriter
from sqlalchemy import update, delete

from api import get_logger
from api.models.models import Book, Section, DbSession, BookStatus
from api.services.files import FilesService
from api.utils.text import ParagraphBuilder, SectionBuilder, LineReader

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
        pdf_file.seek(0)
        pdf_reader = PdfReader(pdf_file)
        page_num = len(pdf_reader.pages)
        section_dicts = split_into_sections(pdf_reader)

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

    def delete_sections(self, book: Book):
        with DbSession() as session:
            stmt = delete(Section).where(Section.book_id == book.id)
            session.execute(stmt)
            session.commit()

def split_into_sections(pdf_reader: PdfReader):
    sections = []

    line_reader = LineReader(pdf_reader)
    while line_reader.has_next():
        section_builder = SectionBuilder()
        while section_builder.need_more_text() and line_reader.has_next():
            paragraph_builder = ParagraphBuilder()
            while paragraph_builder.need_more_text() and line_reader.has_next():
                paragraph_builder.append(line_reader.next())

            if section_builder.page_index is not None and paragraph_builder.page_index != section_builder.page_index:
                sections.append(section_builder.build())
                section_builder = SectionBuilder()

            section_builder.append(paragraph_builder.build())

        sections.append(section_builder.build())

    return sections
