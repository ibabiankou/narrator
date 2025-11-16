import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from api import SessionDep
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
    # TODO: handle not found scenario

    # TODO: Upload file to Object Store.

    # TODO: Store book metadata in DB.

    # TODO: Trigger processing in background.

    resp = BookDetails(id=book.id, title=book.title, pdf_file_name=pdf_temp_file.file_name)
    books[str(resp.id)] = resp
    return resp

@books_router.get("/{book_id}", response_model=BookDetails)
def get_book(book_id: str) -> BookDetails:
    return books[book_id]
