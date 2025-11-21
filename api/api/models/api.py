import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TempFile(BaseModel):
    id: uuid.UUID
    filename: str
    upload_time: datetime


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
    id: int
    book_id: uuid.UUID
    page_index: int
    section_index: int
    content: str


class BookPage(BaseModel):
    index: int
    file_name: str
    sections: list[BookSection]


class BookContent(BaseModel):
    pages: list[BookPage]
