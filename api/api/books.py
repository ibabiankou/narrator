import uuid
from datetime import datetime, UTC
from typing import Annotated

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response, Header
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
                    if_none_match: Annotated[str | None, Header()] = None):
    try:
        file_data = file_service.get_speech_file(book_id, file_name, if_none_match)
    except NotModified:
        return Response(status_code=304)

    if file_data is None:
        raise HTTPException(status_code=404, detail="Speech file not found")
    # Have no idea why, but this header enables seeking in the HTMLAudioElement.
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=604800, immutable",
        "ETag": file_data.etag
    }
    return Response(content=file_data.body, media_type=file_data.content_type, headers=headers)
