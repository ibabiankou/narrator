import io
import uuid
from datetime import datetime, UTC
from typing import Annotated

import m3u8
from fastapi import APIRouter, HTTPException, BackgroundTasks, Response, Header, Request
from m3u8.model import InitializationSection
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from api import SessionDep, get_logger
from api.models import db, api
from api.services.audiotracks import AudioTrackServiceDep
from api.services.books import BookServiceDep
from api.services.files import FilesServiceDep, NotModified
from api.services.sections import SectionServiceDep

LOG = get_logger(__name__)

books_router = APIRouter()


@books_router.post("/")
def create_book(book: api.CreateBookRequest,
                session: SessionDep,
                background_tasks: BackgroundTasks,
                files_service: FilesServiceDep,
                book_service: BookServiceDep,
                audio_tracks_service: AudioTrackServiceDep) -> api.BookDetails:
    # Load temp_file metadata from DB
    pdf_temp_file = session.get(db.TempFile, book.pdf_temp_file_id)
    if pdf_temp_file is None:
        raise HTTPException(status_code=404, detail="PDF file not found")

    # Upload the book file to the object store
    try:
        files_service.store_book_file(book.id, pdf_temp_file)
    except Exception:
        LOG.info("Error uploading book file to object store", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to store book file")

    # Store book metadata in DB
    book = db.Book(id=book.id,
                   title=book.title,
                   file_name=pdf_temp_file.file_name,
                   created_time=datetime.now(UTC),
                   status=db.BookStatus.processing)
    try:
        session.add(book)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Book with this ID already exists")

    # Process the book in the background
    background_tasks.add_task(book_service.split_pages, book)
    background_tasks.add_task(book_service.extract_text, book)

    return api.BookDetails(id=book.id,
                           title=book.title,
                           pdf_file_name=pdf_temp_file.file_name,
                           status=book.status)


@books_router.get("/")
def get_books(session: SessionDep) -> list[api.BookDetails]:
    # Read books from DB ordered by the date they added.
    stmt = select(db.Book).order_by(db.Book.created_time.desc(), db.Book.title)
    books = session.execute(stmt).scalars().all()

    resp = []
    for book in books:
        resp.append(api.BookDetails(id=book.id,
                                    title=book.title,
                                    pdf_file_name=book.file_name,
                                    number_of_pages=book.number_of_pages,
                                    status=book.status))

    return resp


@books_router.get("/{book_id}")
def get_book(book_id: uuid.UUID, session: SessionDep) -> api.BookDetails:
    book = session.get(db.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    return api.BookDetails(id=book.id,
                           title=book.title,
                           pdf_file_name=book.file_name,
                           number_of_pages=book.number_of_pages,
                           status=book.status)


@books_router.post("/{book_id}/reprocess")
def reprocess_book(book_id: uuid.UUID,
                   session: SessionDep,
                   background_tasks: BackgroundTasks,
                   book_service: BookServiceDep,
                   section_service: SectionServiceDep):
    book = session.get(db.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    session.execute(update(db.Book).where(db.Book.id == book.id).values(status=db.BookStatus.processing))
    session.commit()

    section_service.delete_sections(book_id=book.id)

    background_tasks.add_task(book_service.extract_text, book)


@books_router.get("/{book_id}/content")
def get_book_content(book_id: uuid.UUID,
                     session: SessionDep,
                     ) -> api.BookContent:
    book = session.get(db.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.status != db.BookStatus.ready or book.number_of_pages is None:
        # There will be no content, so return immediately.
        return api.BookContent(pages=[])

    db_sections = session.execute(
        select(db.Section).where(db.Section.book_id == book_id).order_by(db.Section.section_index)).scalars().all()

    # Convert into the API model.
    pages = []
    pages_dict = {}
    # For now, I simply generate pages, but I might need to store that data explicitly instead.
    for i in range(book.number_of_pages or 0):
        pages.append(api.BookPage(index=i, file_name=f"{i}.pdf", sections=[]))
        pages_dict[i] = pages[-1]

    for section in db_sections:
        book_section = api.BookSection(id=section.id,
                                       book_id=section.book_id,
                                       page_index=section.page_index,
                                       section_index=section.section_index,
                                       content=section.content)
        pages_dict[section.page_index].sections.append(book_section)
    return api.BookContent(pages=pages)


@books_router.get("/{book_id}/stream")
def stream_book(book_id: uuid.UUID,
                session: SessionDep,
                file_service: FilesServiceDep,
                request: Request
                ):
    book = session.get(db.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    stmt = select(db.AudioTrack).where(db.AudioTrack.book_id == book_id).where(
        db.AudioTrack.status == db.AudioStatus.ready).order_by(db.AudioTrack.playlist_order)
    ready_tracks = list(session.execute(stmt).scalars().all())
    LOG.info("Loaded %s tracks", len(ready_tracks))

    # duration_sum = [0]
    bytes_sum = [0]
    for track in ready_tracks:
        # duration_sum.append(duration_sum[-1] + track.duration)
        bytes_sum.append(bytes_sum[-1] + track.bytes)

    # total_duration = duration_sum[-1]
    total_bytes = bytes_sum[-1]

    # Handle Range Header: "bytes=0-1023"
    range_header = request.headers.get("Range")
    if range_header:
        range_type, range_val = range_header.split("=")
        start_str, sep, end_str = range_val.partition("-")
        if range_type != "bytes":
            raise HTTPException(status_code=400, detail="Only 'bytes' range type is supported.")
    else:
        start_str = "0"
        end_str = None

    start = int(start_str) if start_str else 0
    default_length = 1024 * 1024
    end = min(int(end_str) if end_str else start + default_length - 1, total_bytes - 1)
    content_length = end - start + 1

    LOG.info("Total bytes available %s", total_bytes)
    LOG.info("Processing range: %s-%s", start, end)
    LOG.info("Expected content length: %s", content_length)

    # Find the tracks corresponding to the range request;
    # Load the tracks, concatenate the data.
    content = io.BytesIO()
    content_type = None
    remaining = content_length
    i = 0
    while remaining > 0 and i < len(ready_tracks):
        # Skip tracks outside the range;
        if bytes_sum[i + 1] < start:
            i += 1
            continue

        track = ready_tracks[i]
        track_bytes_start = max(start - bytes_sum[i], 0)
        track_bytes_end = min(track_bytes_start + remaining - 1, track.bytes - 1)
        track_content_length = track_bytes_end - track_bytes_start + 1

        track_range = f"bytes={track_bytes_start}-{track_bytes_end}"
        file_data = file_service.get_speech_file(book_id, track.file_name, range=track_range)
        if file_data is None:
            raise HTTPException(status_code=404, detail=f"Speech file {track.file_name} not found")
        content.write(file_data.body)
        LOG.info("Loaded %s bytes for track %s, requested range %s, out of %s",
                 len(file_data.body), track.file_name, track_range, track.bytes)

        if content_type is None:
            content_type = file_data.content_type
        elif content_type != file_data.content_type:
            raise HTTPException(status_code=500, detail="Tracks have different content types")

        remaining -= track_content_length
        i += 1
        if remaining <= 0:
            break

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{total_bytes}",
        "Content-Length": str(content_length),
    }
    content.seek(0)
    content_bytes = content.read()
    LOG.info("Actual size of bytes loaded: %s", len(content_bytes))
    return Response(
        content=content_bytes,
        status_code=206,
        media_type="audio/ogg",
        headers=headers)


@books_router.get("/{book_id}/stream.m3u8")
def book_playlist(book_id: uuid.UUID,
                session: SessionDep,
                ):
    book = session.get(db.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    stmt = select(db.AudioTrack).where(db.AudioTrack.book_id == book_id).where(
        db.AudioTrack.status == db.AudioStatus.ready).order_by(db.AudioTrack.playlist_order)
    ready_tracks = list(session.execute(stmt).scalars().all())
    LOG.info("Loaded %s tracks", len(ready_tracks))

    return Response(
        content=generate_dynamic_playlist(ready_tracks),
        media_type="application/vnd.apple.mpegurl"
    )

def generate_dynamic_playlist(tracks: list[db.AudioTrack]):
    playlist = m3u8.M3U8()

    playlist.version = 4
    playlist.target_duration = 90
    playlist.media_sequence = 0
    playlist.is_endlist = True  # Set to False for live streams

    for track in tracks:
        # Add a segment with a duration and its URI
        segment = m3u8.Segment(
            uri=f"http://localhost:8000/api/books/{track.book_id}/speech/{track.file_name}",
            duration=track.duration,
            discontinuity=True,
            init_section={"uri": f"http://localhost:8000/api/files/{tracks[0].book_id}/map.mp4"}
        )
        playlist.segments.append(segment)

    return playlist.dumps()

@books_router.get("/{book_id}/pages/{page_file_name}")
def get_book_page(book_id: uuid.UUID,
                  page_file_name: str,
                  file_service: FilesServiceDep,
                  if_none_match: Annotated[str | None, Header()] = None):
    file_data = file_service.get_book_page_file(book_id, page_file_name, if_none_match)
    if file_data is None:
        raise HTTPException(status_code=404, detail="Page not found")
    headers = {
        "Cache-Control": "private, max-age=604800, immutable",
        "ETag": file_data.etag
    }
    return Response(content=file_data.body, media_type=file_data.content_type, headers=headers)


@books_router.get("/{book_id}/speech/{file_name}")
def get_speech_file(book_id: uuid.UUID,
                    file_name: str,
                    file_service: FilesServiceDep,
                    request: Request,
                    if_none_match: Annotated[str | None, Header()] = ""):

    # Handle Range Header: "bytes=0-1023"
    range_header = request.headers.get("Range")
    if range_header:
        range_type, range_val = range_header.split("=")
        start_str, sep, end_str = range_val.partition("-")
        if range_type != "bytes":
            raise HTTPException(status_code=400, detail="Only 'bytes' range type is supported.")
    else:
        start_str = "0"
        end_str = None

    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else -1

    range_request = f"bytes={start}-{end if end != -1 else ''}"

    LOG.info("Processing range: %s, %s", start, end)

    try:
        file_data = file_service.get_speech_file(book_id, file_name, if_none_match, range=range_request)
    except NotModified:
        return Response(status_code=304)

    if file_data is None:
        raise HTTPException(status_code=404, detail="Speech file not found")
    # Have no idea why, but this header enables seeking in the HTMLAudioElement.
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Range": file_data.range,
        "Cache-Control": "private, max-age=604800, immutable",
        "ETag": file_data.etag
    }
    return Response(content=file_data.body, status_code=206, media_type=file_data.content_type, headers=headers)
