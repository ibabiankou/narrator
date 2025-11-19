import uuid
from datetime import datetime, UTC
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from fastapi.params import Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from api import SessionDep, get_logger
from api.models import models
from api.models.models import TempFile, BookStatus
from api.services.books import BookService
from api.services.files import FilesService

LOG = get_logger(__name__)

books_router = APIRouter()


class CreateBookRequest(BaseModel):
    id: uuid.UUID
    title: str
    pdf_temp_file_id: uuid.UUID


class BookDetails(BaseModel):
    id: uuid.UUID
    title: str
    pdf_file_name: str
    number_of_pages: Optional[int] = None
    status: str


class BookSection(BaseModel):
    page_index: int
    section_index: int
    content: str


class BookPage(BaseModel):
    index: int
    file_name: str
    sections: list[BookSection]


class BookContent(BaseModel):
    pages: list[BookPage]


@books_router.post("/")
def create_book(book: CreateBookRequest,
                session: SessionDep,
                background_tasks: BackgroundTasks,
                files_service: FilesService = Depends(),
                book_service: BookService = Depends()) -> BookDetails:
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
    book = models.Book(id=book.id,
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

    return BookDetails(id=book.id,
                       title=book.title,
                       pdf_file_name=pdf_temp_file.file_name,
                       status=book.status)


@books_router.get("/")
def get_books(session: SessionDep) -> list[BookDetails]:
    # Read books from DB ordered by the date they added.
    stmt = select(models.Book).order_by(models.Book.created_time.desc(), models.Book.title)
    books = session.execute(stmt).scalars().all()

    resp = []
    for book in books:
        resp.append(BookDetails(id=book.id,
                                title=book.title,
                                pdf_file_name=book.file_name,
                                number_of_pages=book.number_of_pages,
                                status=book.status))

    return resp


@books_router.get("/{book_id}")
def get_book(book_id: uuid.UUID, session: SessionDep) -> BookDetails:
    book = session.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    return BookDetails(id=book.id,
                       title=book.title,
                       pdf_file_name=book.file_name,
                       number_of_pages=book.number_of_pages,
                       status=book.status)


@books_router.post("/{book_id}/reprocess")
def get_book(book_id: uuid.UUID,
             session: SessionDep,
             background_tasks: BackgroundTasks,
             book_service: BookService = Depends()):
    book = session.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    session.execute(update(models.Book).where(models.Book.id == book.id).values(status=BookStatus.processing))
    session.commit()

    book_service.delete_sections(book)

    background_tasks.add_task(book_service.extract_text, book)


@books_router.get("/{book_id}/content")
def get_book_content(book_id: uuid.UUID, session: SessionDep, last_page_idx: int = 0, limit: int = 10) -> BookContent:
    book = session.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.status != BookStatus.ready or book.number_of_pages is None:
        raise HTTPException(status_code=204, detail="Book is not ready. No content.")

    stmt = select(models.Section).where(models.Section.book_id == book_id)
    # Treat the default value as a special case because page index is 0 based, otherwise we always miss the first page.
    if last_page_idx == 0:
        stmt = stmt.where(models.Section.page_index >= 0).where(models.Section.page_index < limit)
    else:
        stmt = stmt.where(models.Section.page_index > last_page_idx).where(
            models.Section.page_index <= last_page_idx + limit)
    stmt = stmt.order_by(models.Section.section_index)
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
        pages.append(BookPage(index=i, file_name=f"{i}.pdf", sections=[]))
        pages_dict[i] = pages[-1]

    for section in db_sections:
        book_section = BookSection(page_index=section.page_index,
                                   section_index=section.section_index,
                                   content=section.content)
        pages_dict[section.page_index].sections.append(book_section)
    return BookContent(pages=pages)


@books_router.get("/{book_id}/pages/{page_file_name}")
def get_book_page(book_id: uuid.UUID, page_file_name: str, file_service: FilesService = Depends()):
    response_dict = file_service.get_book_page_file(book_id, page_file_name)
    if response_dict is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return Response(content=response_dict["body"], media_type=response_dict["content_type"])
