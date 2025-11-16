import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import SessionDep
from api.models import models
from api.models.models import TempFile

books_router = APIRouter()


class CreateBookRequest(BaseModel):
    id: uuid.UUID
    title: str
    pdf_temp_file_id: uuid.UUID

class BookDetails(BaseModel):
    id: uuid.UUID
    title: str
    pdf_file_name: str

books = {}

@books_router.post("/", response_model=BookDetails)
def create_book(book: CreateBookRequest, session: SessionDep) -> BookDetails:
    # Load temp_file metadata from DB
    pdf_temp_file = session.get(TempFile, book.pdf_temp_file_id)
    if pdf_temp_file is None:
        raise HTTPException(status_code=404, detail="PDF file not found")

    # TODO: Upload file to Object Store.

    session.add(models.Book(id=book.id, title=book.title, file_name=pdf_temp_file.file_name))
    session.commit()

    # TODO: Trigger processing in background. How??

    return BookDetails(id=book.id, title=book.title, pdf_file_name=pdf_temp_file.file_name)

@books_router.get("/{book_id}", response_model=BookDetails)
def get_book(book_id: uuid.UUID, session: SessionDep) -> BookDetails:
    book = session.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    return BookDetails(id=book.id, title=book.title, pdf_file_name=book.file_name)
