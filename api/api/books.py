import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from fastapi.params import Depends
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from api import SessionDep, get_logger
from api.models import db, api
from api.models.db import TempFile, BookStatus
from api.services.books import BookService
from api.services.files import FilesService
from api.services.sections import SectionService

LOG = get_logger(__name__)

books_router = APIRouter()


@books_router.post("/")
def create_book(book: api.CreateBookRequest,
                session: SessionDep,
                background_tasks: BackgroundTasks,
                files_service: FilesService = Depends(),
                book_service: BookService = Depends()) -> api.BookDetails:
    # Load temp_file metadata from DB
    pdf_temp_file = session.get(TempFile, book.pdf_temp_file_id)
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
                   status=BookStatus.processing)
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
                   book_service: BookService = Depends(),
                   section_service: SectionService = Depends()):
    book = session.get(db.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    session.execute(update(db.Book).where(db.Book.id == book.id).values(status=BookStatus.processing))
    session.commit()

    section_service.delete_sections(book.id)

    background_tasks.add_task(book_service.extract_text, book)


@books_router.get("/{book_id}/content")
def get_book_content(book_id: uuid.UUID, session: SessionDep, last_page_idx: int = 0,
                     limit: int = 10) -> api.BookContent:
    book = session.get(db.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.status != BookStatus.ready or book.number_of_pages is None:
        # There will be no content, so return immediately.
        return api.BookContent(pages=[])

    stmt = select(db.Section).where(db.Section.book_id == book_id)
    # Treat the default value as a special case because page index is 0 based, otherwise we always miss the first page.
    if last_page_idx == 0:
        stmt = stmt.where(db.Section.page_index >= 0).where(db.Section.page_index < limit)
    else:
        stmt = stmt.where(db.Section.page_index > last_page_idx).where(
            db.Section.page_index <= last_page_idx + limit)
    stmt = stmt.order_by(db.Section.section_index)
    db_sections = session.execute(stmt).scalars().all()

    # Convert into the API model.
    pages = []
    pages_dict = {}
    # For now I simply generate pages, but I might need to store that data explicitly instead.
    # TODO: consider persisting number of pages as a metadata on Book level.

    # Skip offset for the initial request.
    first_page_offset = 0 if last_page_idx == 0 else 1
    # Don't go beyond the total number of pages.
    last_page = min(last_page_idx + limit + first_page_offset, book.number_of_pages)
    for i in range(last_page_idx + first_page_offset, last_page):
        pages.append(api.BookPage(index=i, file_name=f"{i}.pdf", sections=[]))
        pages_dict[i] = pages[-1]

    for section in db_sections:
        book_section = api.BookSection(id=section.id,
                                       book_id=section.book_id,
                                       page_index=section.page_index,
                                       section_index=section.section_index,
                                       content=section.content,
                                       phonemes=section.phonemes,
                                       speech_status=section.speech_status,
                                       speech_file=section.speech_file)
        pages_dict[section.page_index].sections.append(book_section)
    return api.BookContent(pages=pages)


@books_router.get("/{book_id}/pages/{page_file_name}")
def get_book_page(book_id: uuid.UUID, page_file_name: str, file_service: FilesService = Depends()):
    response_dict = file_service.get_book_page_file(book_id, page_file_name)
    if response_dict is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return Response(content=response_dict["body"], media_type=response_dict["content_type"])


@books_router.get("/{book_id}/speech/{file_name}")
def get_speech_file(book_id: uuid.UUID, file_name: str, file_service: FilesService = Depends()):
    response_dict = file_service.get_speech_file(book_id, file_name)
    if response_dict is None:
        raise HTTPException(status_code=404, detail="Speech file not found")
    return Response(content=response_dict["body"], media_type=response_dict["content_type"])
