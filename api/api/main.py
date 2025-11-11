import uuid
from datetime import datetime

from fastapi import APIRouter, FastAPI, UploadFile
from pydantic import BaseModel, RootModel
from pydantic.v1 import UUID4

app = FastAPI()

base_url_router = APIRouter(prefix="/api")

@base_url_router.get("/")
def health():
    return {"status": "ok"}


class ID(RootModel):
    root: uuid.UUID

class TempFile(BaseModel):
    id: ID
    filename: str
    upload_time: datetime

temp_files = {}

@base_url_router.post("/files/", response_model=TempFile)
def upload_file(file: UploadFile) -> TempFile:
    resp = TempFile(id=uuid.uuid4(), filename=file.filename, upload_time=datetime.utcnow())
    # TODO: Write file to disk and store metadata in DB.
    temp_files[str(resp.id)] = resp
    return resp


class CreateBookRequest(BaseModel):
    id: ID
    title: str
    pdf_temp_file_id: ID

class BookDetails(BaseModel):
    id: ID
    title: str
    pdf_file_name: str

books = {}

@base_url_router.post("/books/", response_model=BookDetails)
def create_book(book: CreateBookRequest) -> BookDetails:
    pdf_temp_file = temp_files.get(str(book.pdf_temp_file_id))
    resp = BookDetails(id=book.id, title=book.title, pdf_file_name=pdf_temp_file.filename)
    books[str(resp.id)] = resp
    return resp

@base_url_router.get("/books/{book_id}", response_model=BookDetails)
def get_book(book_id: ID) -> BookDetails:
    return books[str(resp.id)]

app.include_router(base_url_router)
