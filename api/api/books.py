import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.params import Depends
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from api import SessionDep
from api.models import models
from api.models.models import TempFile
from api.services.books import BookService
from api.services.files import FilesService

books_router = APIRouter()


class CreateBookRequest(BaseModel):
    id: uuid.UUID
    title: str
    pdf_temp_file_id: uuid.UUID

class BookDetails(BaseModel):
    id: uuid.UUID
    title: str
    pdf_file_name: str

@books_router.post("/", response_model=BookDetails)
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
        raise HTTPException(status_code=500, detail="Failed to store book file")

    # Store book metadata in DB
    book = models.Book(id=book.id, title=book.title, file_name=pdf_temp_file.file_name)
    try:
        session.add(book)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Book with this ID already exists")

    # Process book file in the background
    background_tasks.add_task(book_service.parse_book, book)

    return BookDetails(id=book.id, title=book.title, pdf_file_name=pdf_temp_file.file_name)

@books_router.get("/{book_id}", response_model=BookDetails)
def get_book(book_id: uuid.UUID, session: SessionDep) -> BookDetails:
    book = session.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    return BookDetails(id=book.id, title=book.title, pdf_file_name=book.file_name)
