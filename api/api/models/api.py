import uuid
from datetime import datetime
from typing import Optional, Generic, List, TypeVar

from fastapi import Query
from pydantic import BaseModel

from api.models import db

T = TypeVar("T")


class TempFile(BaseModel):
    id: uuid.UUID
    filename: str
    upload_time: datetime


class CreateBookRequest(BaseModel):
    id: uuid.UUID
    title: str
    pdf_temp_file_id: uuid.UUID


class PageRequest(BaseModel):
    page: int = Query(1, ge=1, description="Page number")
    size: int = Query(2, ge=1, le=100, description="Items per page")


class PagedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int


class BookOverview(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    pdf_file_name: str
    number_of_pages: Optional[int] = None
    status: str
    cover: Optional[str] = None

    @classmethod
    def from_orm(cls, book: db.Book):
        return BookOverview(id=book.id,
                            owner_id=book.owner_id,
                            title=book.title,
                            pdf_file_name=book.file_name,
                            number_of_pages=book.number_of_pages,
                            status=book.status,
                            cover=book.cover)


class BookStats(BaseModel):
    # Seconds narrated so far.
    total_narrated_seconds: float
    # Percentage of the total book that is narrated.
    available_percent: float
    # Sum of every audio_track size in bytes.
    total_size_bytes: int


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


class BookWithContent(BaseModel):
    overview: BookOverview
    stats: BookStats
    pages: list[BookPage]


class AudioTrack(BaseModel):
    book_id: uuid.UUID
    section_id: int
    status: str
    file_name: Optional[str]
    duration: Optional[float]


class PlaybackInfo(BaseModel):
    book_id: uuid.UUID
    data: dict


class SetCover(BaseModel):
    file_path: str
