from fastapi import APIRouter
from pydantic import BaseModel

from api.api_models import ID
from api.files import temp_files

books_router = APIRouter()


class CreateBookRequest(BaseModel):
    id: ID
    title: str
    pdf_temp_file_id: ID

class BookDetails(BaseModel):
    id: ID
    title: str
    pdf_file_name: str

books = {}

@books_router.post("/", response_model=BookDetails)
def create_book(book: CreateBookRequest) -> BookDetails:
    pdf_temp_file = temp_files.get(str(book.pdf_temp_file_id))
    resp = BookDetails(id=book.id, title=book.title, pdf_file_name=pdf_temp_file.filename)
    books[str(resp.id)] = resp
    return resp

@books_router.get("/{book_id}", response_model=BookDetails)
def get_book(book_id: str) -> BookDetails:
    return books[book_id]
