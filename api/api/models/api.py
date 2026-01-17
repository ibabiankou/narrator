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


class BookOverview(BaseModel):
    id: uuid.UUID
    title: str
    pdf_file_name: str
    number_of_pages: Optional[int] = None
    status: str


class BookStats(BaseModel):
    # Seconds narrated so far.
    total_narrated_seconds: float
    # Percentage of the total book that is narrated.
    available_percent: float


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
