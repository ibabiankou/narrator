from concurrent.futures import ProcessPoolExecutor

import asyncio
import logging
import m3u8
import uuid
from datetime import datetime, UTC
from fastapi import BackgroundTasks
from io import BytesIO
from sqlalchemy import update, text, select
from sqlalchemy.sql.functions import count
from typing import Annotated, List

from api.models import api, db, domain
from api.models.db import NarrationQueue
from api.models.narration import NarrationManifest
from api.services.epub import EpubServiceDep
from api.services.files import FilesServiceDep
from api.services.progress import PlaybackProgressServiceDep
from api.utils.imgproxy import ImgProxy
from common_lib.db import transactional
from common_lib.service import Service
from epub_lib import Epub

LOG = logging.getLogger(__name__)

executor = ProcessPoolExecutor(max_workers=4)


# noinspection PyTypeChecker
class BookService(Service):
    def __init__(self,
                 files_service: FilesServiceDep,
                 playback_progress_service: PlaybackProgressServiceDep,
                 epub_service: EpubServiceDep,
                 **kwargs):
        self.files_service = files_service
        self.playback_progress_service = playback_progress_service
        self.epub_service = epub_service

        self.img_proxy = ImgProxy()

    @transactional
    def create_book(self, user_id: uuid.UUID, file_name: str, file_bytes: BytesIO,
                    background_tasks: BackgroundTasks):

        # Extract metadata
        epub = Epub(file_bytes, filename=file_name)
        titles = epub.package.metadata.get_title()
        authors = epub.package.metadata.get_authors()
        descriptions = epub.package.metadata.get_descriptions()

        if not epub.package.metadata.has_english_language():
            raise ValueError("Only English language is supported at the moment.")

        # TODO: process identifiers.

        book_id = uuid.uuid4()
        cover_image_maybe = epub.get_cover_image()
        cover_thumbnail_path = None
        if cover_image_maybe is not None:
            image_name, mime_type, image_bytes = cover_image_maybe
            # TODO: compress image right away.
            cover_image_key = f"{book_id}/images/{image_name}"
            self.files_service.upload_file(cover_image_key, image_bytes)
            cover_thumbnail_path = self.img_proxy.build_url(cover_image_key)

        file_bytes.seek(0)
        self.files_service.upload_file(f"{book_id}/epub-files/source.epub", file_bytes)

        file_bytes = self.epub_service.remove_links(file_bytes)
        file_bytes, fragment_map = self.epub_service.inline_fragments(file_bytes)
        self.files_service.upload_file(f"{book_id}/epub-files/fragmented.epub", file_bytes)

        publication_content = epub.get_publication_content()
        narration_manifest = self.epub_service.build_narration_manifest(publication_content, fragment_map)
        narration_manifest_bytes = narration_manifest.model_dump_json().encode()
        self.files_service.upload_file(f"{book_id}/narration-manifest.json", narration_manifest_bytes)

        # TODO: Compress images;

        file_bytes.seek(0)
        book = db.Book(id=book_id,
                       owner_id=user_id,
                       file_name=file_name,
                       created_time=datetime.now(UTC),
                       status=db.BookStatus.ready_for_toc_review,
                       cover=cover_thumbnail_path,
                       title=titles[0],
                       authors=authors,
                       description=descriptions[0] if len(descriptions) > 0 else None
                       )

        self.db.add(book)

        return api.BookOverview.from_orm(book)

    def _set_status(self, book_id: uuid.UUID, status: db.BookStatus):
        self.db.execute(update(db.Book).where(db.Book.id == book_id).values(status=status))

    def _set_candidates(self, book_id: uuid.UUID, metadata_candidates: domain.MetadataCandidates):
        self.db.execute(update(db.Book).where(db.Book.id == book_id).values(metadata_candidates=metadata_candidates))

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
            if self.img_proxy.is_img_proxy_url(metadata.cover):
                cover_thumbnail = metadata.cover
            else:
                cover_thumbnail = self.img_proxy.build_url(metadata.cover)

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
        pass

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
        query_text = """select b.id,
                               (select count(*) from narration_queue q where q.completed is null and q.book_id = b.id) as pending_count
                        from books b
                        where b.status = 'narrating';
                     """
        book_narration_stats_maybe = self.db.execute(text(query_text)).one_or_none()
        if book_narration_stats_maybe is None:
            LOG.info("No book is being narrated, doing nothing.")
            return

        book_id, pending_count = book_narration_stats_maybe
        if pending_count == 0:
            LOG.info("Narration of book %s completed.", book_id)
            # TODO: Implement some kind of sanity check and clean up narration_queue table.
            self._set_status(book_id, db.BookStatus.ready)

    @transactional
    def get_book_details(self, book_id: uuid.UUID) -> api.BookDetails:
        return api.BookDetails.from_orm(self.db.get_one(db.Book, book_id))

    @transactional
    def get_table_of_contents(self, book_id: uuid.UUID) -> List[api.TableOfContentsItem]:
        manifest_bytes = self.files_service.get_book_file(book_id, "narration-manifest.json")
        manifest: NarrationManifest = NarrationManifest.model_validate_json(manifest_bytes.getvalue())

        toc_items = []
        for content_file in manifest.root:
            for nav_item in content_file.navigation_items:
                href = content_file.href if nav_item.idref is None else f"{content_file.href}#{nav_item.idref}"
                toc_items.append(api.TableOfContentsItem(
                    href=href,
                    title=nav_item.title,
                    narrate=nav_item.narrate))

        return toc_items

    @transactional
    def narrate_book(self, book_id: uuid.UUID, narration_request: List[api.TableOfContentsItem]):
        # TODO: allow user to select the model and voice. For now, just hardcode kokoro and michael.
        tts_model = "kokoro"
        voice = "am_michael"

        db_narration_request = []
        for item in narration_request:
            db_narration_request.append(db.TocItem(href=item.href, narrate=item.narrate))
        self.db.execute(update(db.Book).where(db.Book.id == book_id)
                        .values(narration_request=db_narration_request, status=db.BookStatus.queued))

        manifest_bytes = self.files_service.get_book_file(book_id, "narration-manifest.json")
        manifest: NarrationManifest = NarrationManifest.model_validate_json(manifest_bytes.getvalue())

        should_narrate_map = {i.href: i.narrate for i in narration_request}

        items_to_enqueue = []
        for content_file in manifest.root:
            for nav_item in content_file.navigation_items:
                href = content_file.href if nav_item.idref is None else f"{content_file.href}#{nav_item.idref}"
                should_narrate_maybe = should_narrate_map.get(href)
                if should_narrate_maybe is None:
                    LOG.warning("Unknown content href '%s', default to narrating it.", href)

                if should_narrate_maybe is None or should_narrate_maybe:
                    for track in nav_item.audio_tracks:
                        queue_item = NarrationQueue(
                            book_id=book_id,
                            tts_model=tts_model,
                            voice=voice,
                            track_base_name=track.name,
                            order=track.fragment_groups.root[0].root[0].id,
                            fragments=track.fragment_groups,
                            added=datetime.now(UTC)
                        )
                        items_to_enqueue.append(queue_item)
        self.db.add_all(items_to_enqueue)

        master_playlist = self._generate_master_playlist(book_id=book_id, model=tts_model, voice=voice)
        master_playlist_key = f"{book_id}/playlists/master.m3u8"
        self.files_service.upload_file(master_playlist_key, master_playlist.encode())


    def _generate_master_playlist(self, book_id: uuid.UUID, model: str, voice: str) -> str:
        playlist = m3u8.M3U8()

        playlist.version = "4"

        pl = m3u8.Playlist(
            uri=f"/api/files/{book_id}/playlists/{model}_{voice}.m3u8",
            stream_info={
                "bandwidth": 96000,
                "audio": "voices"
            },
            media=[],
            base_uri="",
        )
        playlist.add_playlist(pl)

        voice_media = m3u8.Media(
            type="audio",
            group_id="voices",
            name=f"{model} {voice}",
            default="yes",
            autoselect="yes",
            language="en"
        )
        playlist.add_media(voice_media)

        return playlist.dumps()



BookServiceDep = Annotated[BookService, BookService.dep()]
