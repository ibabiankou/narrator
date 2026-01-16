import os
import uuid
from datetime import datetime, UTC

import m3u8
from fastapi import APIRouter, HTTPException, BackgroundTasks, Response, Header, Request
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, NoResultFound

from api import SessionDep, get_logger
from api.models import db, api
from api.services.books import BookServiceDep
from api.services.files import FilesServiceDep
from api.services.sections import SectionServiceDep

LOG = get_logger(__name__)

books_router = APIRouter(tags=["Books API"])


@books_router.post("/")
def create_book(book: api.CreateBookRequest,
                session: SessionDep,
                background_tasks: BackgroundTasks,
                files_service: FilesServiceDep,
                book_service: BookServiceDep) -> api.BookDetails:
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

@books_router.delete("/{book_id}", status_code=204)
def delete_book(book_id: uuid.UUID, book_service: BookServiceDep):
    try:
        book_service.delete_book(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")

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


@books_router.get("/{book_id}/m3u8")
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
    base_url = os.getenv("BASE_URL", "http://localhost:8000/api")

    playlist = m3u8.M3U8()

    playlist.version = "4"
    playlist.target_duration = max([t.duration for t in tracks]) + 1
    playlist.media_sequence = 0
    # TODO: What would be behavior if I set it to False? Would it help for books that are being generated?
    playlist.is_endlist = True  # Set to False for live streams

    for track in tracks:
        # Add a segment with a duration and its URI
        segment = m3u8.Segment(
            uri=f"{base_url}/files/{track.book_id}/speech/{track.file_name}",
            duration=track.duration,
            discontinuity=True,
            # TODO: Add daterange tag with X-SID="section-id", X-ORDER="ddd", X-DURATION="ddd" allowing
            #  to sync what is playing with what is
            dateranges=[]
        )
        playlist.segments.append(segment)

    return playlist.dumps()
