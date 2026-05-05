import asyncio
import hashlib
import logging
import uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, UTC
from io import BytesIO
from typing import Annotated

import pymupdf
from fastapi import BackgroundTasks
from pypdf import PdfReader, PdfWriter
from sqlalchemy import update, text, select
from sqlalchemy.sql.functions import count

from api.models import api, db, domain
from api.openlibrary.service import OpenlibraryServiceDep
from api.services.experimental import identify_book
from api.services.files import FilesServiceDep
from api.services.progress import PlaybackProgressServiceDep
from api.services.sections import SectionServiceDep
from api.utils.text import LineReader, CleanupPipeline, pages_to_paragraphs, \
    paragraphs_to_sections
from common_lib.db import transactional
from common_lib.service import Service

LOG = logging.getLogger(__name__)

executor = ProcessPoolExecutor(max_workers=4)


# noinspection PyTypeChecker
class BookService(Service):
    def __init__(self,
                 files_service: FilesServiceDep,
                 sections_service: SectionServiceDep,
                 playback_progress_service: PlaybackProgressServiceDep,
                 openlibrary_service: OpenlibraryServiceDep,
                 **kwargs):
        self.files_service = files_service
        self.sections_service = sections_service
        self.playback_progress_service = playback_progress_service
        self.openlibrary_service = openlibrary_service

    @transactional
    def create_book_v2(self, user_id: uuid.UUID, file_name: str, file_bytes: BytesIO,
                       background_tasks: BackgroundTasks):
        # TODO: Validate language. Fail book creation if language is not supported.

        book_id = uuid.uuid4()
        file_key = f"{book_id}/{file_name}"

        file_bytes.seek(0)
        self.files_service.upload_file(file_key, file_bytes)

        file_bytes.seek(0)
        pdf_document = pymupdf.open(stream=file_bytes, filetype="application/pdf")

        book = db.Book(id=book_id,
                       owner_id=user_id,
                       file_name=file_name,
                       created_time=datetime.now(UTC),
                       number_of_pages=pdf_document.page_count,
                       status=db.BookStatus.processing)

        self.db.add(book)

        background_tasks.add_task(self.extract_metadata, book_id, file_name)
        background_tasks.add_task(self.split_pages, book_id, file_name)
        background_tasks.add_task(self.extract_text, book_id, file_name)

        return api.BookOverview.from_orm(book)

    def split_pages(self, book_id: uuid.UUID, book_file_name: str):
        LOG.debug(f"Splitting book {book_id} into pages.")

        pdf_bytes = self.files_service.get_book_file(book_id, book_file_name)

        # Split it into individual page files
        pdf_pages = self._split_into_pages(pdf_bytes)

        # Upload page files to the object store
        self.files_service.upload_book_pages(book_id, pdf_pages)

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

    def get_text(self, book: db.Book, first_page: int = None, last_page: int = None, raw: bool = False):
        pdf_bytes = self.files_service.get_book_file(book.id, book.file_name)
        return self._get_text(pdf_bytes, first_page, last_page, raw)

    def _get_text(self, pdf_bytes: BytesIO, first_page: int = None, last_page: int = None, raw: bool = False):
        pdf_bytes.seek(0)
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
        pdf_bytes = self.files_service.get_book_file(book.id, book.file_name)
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

    @transactional
    def extract_text(self, book_id: uuid.UUID, book_file_name: str):
        LOG.info(f"Extracting text of the book {book_id}")

        # Split each page into sections. A section is one or more paragraphs.
        pdf_bytes = self.files_service.get_book_file(book_id, book_file_name)

        doc = pymupdf.open(stream=pdf_bytes, filetype="application/pdf")
        pages = [p.get_text() for p in doc]
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

        self.db.add_all(sections)

    def _set_status(self, book_id: uuid.UUID, status: db.BookStatus):
        self.db.execute(update(db.Book).where(db.Book.id == book_id).values(status=status))

    def _set_candidates(self, book_id: uuid.UUID, metadata_candidates: domain.MetadataCandidates):
        self.db.execute(update(db.Book).where(db.Book.id == book_id).values(metadata_candidates=metadata_candidates))

    @transactional
    def extract_metadata(self, book_id: uuid.UUID, book_file_name: str, update_metadata: bool = True,
                         update_status: bool = True):
        LOG.info(f"Extracting metadata of the book {book_id}")
        pdf_bytes = self.files_service.get_book_file(book_id, book_file_name)

        first_pages = self._get_text(pdf_bytes, 0, 10, False)
        llm_metadata = identify_book(first_pages)

        llm_candidate = domain.MetadataCandidate(source="gemini", **llm_metadata.model_dump())

        image_filenames = self._extract_and_store_images(book_id, pdf_bytes)
        if len(image_filenames) > 0:
            # Assume the first image is the book cover image.
            thumbnail_path = self.files_service.create_thumbnail(book_id, image_filenames[0])
            self.set_cover(book_id, thumbnail_path)
            llm_candidate.cover = image_filenames[0]

        ol_candidates = self.openlibrary_service.search_matches(book_id, llm_candidate)

        all_candidates = [llm_candidate] + ol_candidates
        metadata_candidates = domain.MetadataCandidates(candidates=all_candidates, preferred_index=0,
                                                        selected_index=None)

        self._set_candidates(book_id, metadata_candidates)
        if update_metadata:
            self.update_metadata(book_id, llm_metadata)
        if update_status:
            self._set_status(book_id, db.BookStatus.ready_for_metadata_review)

    @transactional
    def extract_and_store_images(self, book_id: uuid.UUID, book_file_name: str):
        pdf_bytes = self.files_service.get_book_file(book_id, book_file_name)
        self._extract_and_store_images(book_id, pdf_bytes)

    def _extract_and_store_images(self, book_id: uuid.UUID, pdf_bytes: BytesIO) -> list[str]:
        """Extracts all images found in the given PDF file and uploads them to files_service.
        Returns the list of uploaded file names."""
        LOG.info(f"Extracting images of the book {book_id}")
        pdf_bytes.seek(0)

        images = self._extract_images(book_id, pdf_bytes)
        for image in images:
            self.files_service.upload_file(image['file_name'], image['content'])

        return [image['file_name'] for image in images]

    def _extract_images(self, book_id: uuid.UUID, pdf_bytes: BytesIO):
        pdf_bytes.seek(0)
        pdf_reader = PdfReader(pdf_bytes)

        # Deduplicate images by hashing them.
        known_hashes = set()
        extracted_images = []

        for page_index, page in enumerate(pdf_reader.pages):
            try:
                for image_file_object in page.images:
                    file_name = f"page{page_index}_{image_file_object.name}"
                    file_key = f"{book_id}/images/{file_name}"

                    hash_obj = hashlib.md5()
                    hash_obj.update(image_file_object.data)

                    file_hash = hash_obj.hexdigest()
                    if file_hash in known_hashes:
                        LOG.info(f"Skipping duplicate image: {file_name}")
                        continue
                    else:
                        LOG.info(f"Extracting image: {file_name}")
                        known_hashes.add(file_hash)

                    extracted_images.append({"file_name": file_key, "content": BytesIO(image_file_object.data)})
            except Exception as e:
                LOG.error("Skipping page %s due to error %s", page_index, e)
                continue

        LOG.info(f"Extracted {len(extracted_images)} images: {[i["file_name"] for i in extracted_images]}")
        return extracted_images

    @transactional
    def set_cover(self, book_id: uuid.UUID, cover_file_name: str):
        self.db.execute(update(db.Book).where(db.Book.id == book_id).values(cover=cover_file_name))

    @transactional
    def get_book(self, book_id: uuid.UUID) -> db.Book:
        return self.db.get_one(db.Book, book_id)

    @transactional
    def get_book_overview(self, book_id: uuid.UUID) -> api.BookOverview:
        return api.BookOverview.from_orm(self.db.get_one(db.Book, book_id))

    @transactional
    def delete_book(self, user_id: uuid.UUID, book_id: uuid.UUID):
        book = self.db.get_one(db.Book, book_id)

        self.playback_progress_service.delete(user_id=user_id, book_id=book_id)
        self.sections_service.delete_sections(book_id=book_id)
        self.files_service.delete_book_files(book_id=book_id)

        self.db.delete(book)

    @transactional
    def get_stats(self, book_id: uuid.UUID) -> dict:
        query = """
                select count(s.id) as length, 'total' as type
                from sections s
                where s.book_id = :book_id
                union
                select coalesce(sum(a.duration), 0) as length, 'narrated_duration' as type
                from audio_tracks a
                where a.book_id = :book_id
                union
                select count(a.id) as length, 'available' as type
                from audio_tracks a
                where a.book_id = :book_id
                  and a.status = 'ready'
                union
                select coalesce(sum(a.bytes), 0) as length, 'total_size_bytes' as type
                from audio_tracks a
                where a.book_id = :book_id
                """

        book_stats = {}
        rs = self.db.execute(text(query), {"book_id": book_id})
        for length, stat_type in rs:
            book_stats[stat_type] = length
        return book_stats

    @transactional
    def is_owner(self, user_id: uuid.UUID, book_id: uuid.UUID) -> bool:
        query = "select owner_id = :owner_id from books where id = :book_id"
        return self.db.execute(text(query), {"owner_id": user_id, "book_id": book_id}).scalar()

    @transactional
    def update_metadata(self, book_id: uuid.UUID, metadata: api.BookMetadata) -> api.BookOverview:
        book = self.db.get_one(db.Book, book_id)

        cover_thumbnail = book.cover
        if metadata.cover is not None and book.cover != metadata.cover:
            cover_thumbnail = self.files_service.create_thumbnail(book_id, metadata.cover)

        # Don't change status back to ready_for_content_review.
        status = book.status if book.status > db.BookStatus.ready_for_metadata_review else db.BookStatus.ready_for_content_review
        stmt = (
            update(db.Book).where(db.Book.id == book_id)
            .values(cover=cover_thumbnail,
                    title=metadata.title,
                    series=metadata.series,
                    description=metadata.description,
                    authors=metadata.authors,
                    isbns=metadata.isbns,
                    status=status)
            .returning(db.Book)
        )
        result = self.db.execute(stmt)
        return api.BookOverview.from_orm(result.scalars().one())

    @transactional
    def list_books(self, user_id: uuid.UUID, page_request: api.PageRequest) -> api.PagedResponse[api.BookOverview]:
        count_stmt = (
            select(count())
            .where(db.Book.owner_id == user_id)
        )
        total = self.db.execute(count_stmt).scalar()

        items_stmt = (
            select(db.Book)
            .where(db.Book.owner_id == user_id)
            .order_by(db.Book.created_time.desc(), db.Book.title)
            .offset(page_request.page_index * page_request.size)
            .limit(page_request.size)
        )
        items = self.db.execute(items_stmt).scalars().all()

        resp = []
        for book in items:
            resp.append(api.BookOverview.from_orm(book))

        return api.paged_response(items=resp, total=total, index=page_request.page_index, size=page_request.size)

    @transactional
    def search_books(self, user_id: uuid.UUID, search_query: str, page_request: api.PageRequest) -> api.PagedResponse[
        api.BookOverview]:
        search_filter = f"%{search_query}%"

        count_stmt = (
            select(count())
            .where(db.Book.title.ilike(search_filter))
            .where(db.Book.owner_id == user_id)
        )
        total = self.db.execute(count_stmt).scalar()

        stmt = (
            select(db.Book)
            .where(db.Book.title.ilike(search_filter))
            .where(db.Book.owner_id == user_id)
            .order_by(db.Book.created_time.desc(), db.Book.title)
            .offset(page_request.page_index * page_request.size)
            .limit(page_request.size)
        )
        books = self.db.execute(stmt).scalars().all()

        resp = []
        for book in books:
            resp.append(api.BookOverview.from_orm(book))

        return api.paged_response(items=resp, total=total, index=page_request.page_index, size=page_request.size)

    @transactional
    def metadata_for_review(self, book_id: uuid.UUID) -> api.BookMetadataForReview:
        book = self.db.get_one(db.Book, book_id)
        overview = api.BookOverview.from_orm(book)
        metadata_candidates = book.metadata_candidates if book.metadata_candidates is not None else domain.MetadataCandidates(
            candidates=[])

        return api.BookMetadataForReview(overview=overview, metadata_candidates=metadata_candidates)

    @transactional
    def process_book(self, book_id, task_name, background_tasks):
        book = self.get_book(book_id)

        if task_name == "split-pages":
            background_tasks.add_task(self.split_pages, book.id, book.file_name)

        if task_name == "extract-text":
            background_tasks.add_task(self.extract_text, book.id, book.file_name)

        if task_name == "extract-images":
            background_tasks.add_task(self.extract_and_store_images, book.id, book.file_name)

        if task_name == "extract-metadata":
            background_tasks.add_task(self.extract_metadata, book.id, book.file_name, False, False)

    @transactional
    def update_status(self, book_id: uuid.UUID, status: db.BookStatus):
        self._set_status(book_id, status)

    async def start_narration_maybe(self):
        while True:
            LOG.info("Checking if need to start narration of a book...")
            try:
                self._do_start_narration_maybe()
            except:
                LOG.info("Error while selecting book to narrate, will try again later.", exc_info=True)
            # TODO: Move the delay duration into system configuration.
            await asyncio.sleep(15)

    @transactional
    def _do_start_narration_maybe(self):
        """If no books are being narrated, pick one from the queue."""

        # Count books with the status
        count_stmt = (
            select(count())
            .where(db.Book.status == db.BookStatus.narrating)
        )
        count_narrating = self.db.execute(count_stmt).scalar()
        if count_narrating > 0:
            LOG.info("%s books already being narrated, not adding more.", count_narrating)
            return

        # Select one book to be narrated.
        query_text = """select b.id
                        from books b
                        where b.status = :status
                        order by b.created_time
                        limit 1
                     """
        book_id_maybe = self.db.execute(text(query_text), {"status": db.BookStatus.queued}).one_or_none()
        if book_id_maybe is None:
            LOG.info("The queue seem to be empty. Doing nothing.")
            return
        else:
            book_id = book_id_maybe[0]
            LOG.info("Starting narration of book %s.", book_id)
            self._set_status(book_id, db.BookStatus.narrating)

    async def complete_narration_maybe(self):
        await asyncio.sleep(5)

        while True:
            LOG.info("Checking if need to complete narration of a book...")
            try:
                self._do_complete_narration_maybe()
            except:
                LOG.info("Error while checking if book narration completed, will try again later.", exc_info=True)
            # TODO: Move the delay duration into system configuration.
            await asyncio.sleep(15)

    @transactional
    def _do_complete_narration_maybe(self):
        """Update status if narration of a book is complete."""
        # select book_id, count of sections and count of finished audio tracks.
        query_text = """select b.id,
                               (select count(*) from sections s where s.book_id = b.id)                            as section_count,
                               (select count(*) from audio_tracks t where t.book_id = b.id and t.status = 'ready') as ready_track_count
                        from books b
                        where b.status = 'narrating';
                     """
        book_narration_stats_maybe = self.db.execute(text(query_text)).one_or_none()
        if book_narration_stats_maybe is None:
            LOG.info("No book is being narrated, doing nothing.")
            return

        book_id, section_count, ready_track_count = book_narration_stats_maybe
        if ready_track_count == section_count:
            LOG.info("Narration of book %s completed.", book_id)
            self._set_status(book_id, db.BookStatus.ready)


BookServiceDep = Annotated[BookService, BookService.dep()]
