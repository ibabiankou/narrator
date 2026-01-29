import io
import uuid
from datetime import datetime, UTC
from io import BytesIO
from typing import Annotated

import pymupdf
from pypdf import PdfReader, PdfWriter
from sqlalchemy import update, text
from sqlalchemy.exc import IntegrityError

from api import get_logger
from api.models import api, db
from api.models.db import DbSession
from api.services.files import FilesServiceDep
from api.services.progress import PlaybackProgressServiceDep
from api.services.sections import SectionServiceDep
from api.utils.text import LineReader, CleanupPipeline, pages_to_paragraphs, \
    paragraphs_to_sections
from common_lib.service import Service

LOG = get_logger(__name__)


class BookService(Service):
    def __init__(self,
                 files_service: FilesServiceDep,
                 sections_service: SectionServiceDep,
                 playback_progress_service: PlaybackProgressServiceDep):
        self.files_service = files_service
        self.sections_service = sections_service
        self.playback_progress_service = playback_progress_service

    def create_book(self, book: api.CreateBookRequest) -> api.BookOverview:
        # Upload the book file to the object store
        try:
            book_file_name = self.files_service.store_book_file(book.id, book.pdf_temp_file_id)
        except Exception as e:
            LOG.info("Error uploading book file to object store", exc_info=True)
            raise e

        # Store book metadata in DB
        book = db.Book(id=book.id,
                       title=book.title,
                       file_name=book_file_name,
                       created_time=datetime.now(UTC),
                       status=db.BookStatus.processing)
        with DbSession() as session:
            try:
                session.add(book)
                session.commit()
            except IntegrityError as e:
                session.rollback()
                raise e
            return api.BookOverview(id=book.id,
                                    title=book.title,
                                    pdf_file_name=book.file_name,
                                    status=book.status)

    def split_pages(self, book_id: uuid.UUID, book_file_name: str):
        LOG.debug(f"Splitting book {book_id} into pages.")

        pdf_file_key = f"{book_id}/{book_file_name}"
        pdf_file_data = self.files_service._get_object(pdf_file_key)

        # Split it into individual page files
        pdf_pages = self._split_into_pages(io.BytesIO(pdf_file_data.body))

        # Upload page files to the object store
        self.files_service.upload_book_pages(book_id, pdf_pages)

    def get_text(self, book: db.Book, first_page: int = None, last_page: int = None, raw: bool = False):
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

    def get_paragraphs(self, book: db.Book, first_page: int = None, last_page: int = None):
        pdf_bytes = self.files_service.get_book_file(book)
        doc = pymupdf.open(stream=pdf_bytes, filetype="application/pdf")
        pages = [p.get_text() for p in doc]

        result = []
        for p in pages_to_paragraphs(pages):
            if first_page is not None and p[0] < first_page:
                continue
            if last_page is not None and p[0] > last_page:
                break
            result.append(str(p))

        return "\n".join(result)

    def extract_text(self, book_id: uuid.UUID, book_file_name: str):
        LOG.info(f"Extracting text of the book {book_id}")

        # Split each page into sections. A section is one or more paragraphs.
        pdf_file_key = f"{book_id}/{book_file_name}"
        pdf_file_data = self.files_service._get_object(pdf_file_key)
        pdf_bytes = io.BytesIO(pdf_file_data.body)

        doc = pymupdf.open(stream=pdf_bytes, filetype="application/pdf")
        pages = [p.get_text() for p in doc]
        page_num = len(pages)
        paragraphs = pages_to_paragraphs(pages)
        section_dicts = paragraphs_to_sections(paragraphs)

        # Persist Sections in DB.
        sections = []
        for section_index in range(len(section_dicts)):
            section_dict = section_dicts[section_index]
            section = db.Section(book_id=book_id,
                                 page_index=section_dict["page_index"],
                                 section_index=section_index,
                                 content=section_dict["content"])
            sections.append(section)

        with DbSession() as session:
            session.add_all(sections)
            session.execute(
                update(db.Book).where(db.Book.id == book_id).values(status=db.BookStatus.ready,
                                                                    number_of_pages=page_num))
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

    def get_book(self, book_id: uuid.UUID) -> db.Book:
        with DbSession() as session:
            return session.get_one(db.Book, book_id)

    def delete_book(self, book_id: uuid.UUID):
        book = self.get_book(book_id)

        self.playback_progress_service.delete(book_id=book_id)
        self.sections_service.delete_sections(book_id=book_id)
        self.files_service.delete_book_files(book_id=book_id)

        with DbSession() as session:
            session.delete(book)
            session.commit()

    def get_stats(self, book_id: uuid.UUID) -> dict:
        query = """
                select coalesce(sum(length(s.content)), 0) as length, 'total' as type
                from sections s
                where s.book_id = :book_id
                union
                select coalesce(sum(a.duration), 0) as length, 'narrated_duration' as type
                from audio_tracks a
                where a.book_id = :book_id
                union
                select coalesce(sum(length(s.content)), 0) as length, 'available' as type
                from sections s
                         join audio_tracks a on s.id = a.section_id
                where s.book_id = :book_id
                  and a.status = 'ready'
                """

        book_stats = {}
        with DbSession() as session:
            rs = session.execute(text(query), {"book_id": book_id})
            for length, stat_type in rs:
                book_stats[stat_type] = length
        return book_stats


BookServiceDep = Annotated[BookService, BookService.dep()]
