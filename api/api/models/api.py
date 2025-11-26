import uuid
from datetime import datetime
from enum import StrEnum
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


class AudioTrack(BaseModel):
    section_id: int
    status: str
    file_name: Optional[str]
    duration: Optional[float]


class PlaybackProgress(BaseModel):
    # ID of the section that was playing last time progress was recorded.
    section_id: Optional[int]

    # Seconds within the section_id where playback was last time recorded.
    section_progress_seconds: Optional[float]

    # Seconds since the start of the book.
    global_progress_seconds: float

    # Seconds narrated so far.
    total_narrated_seconds: float

    # Percentage of the total book that is narrated.
    available_percent: float

    # Percentage of the total book that is queued to be narrated.
    queued_percent: float

    # Percentage of the total book that is not narrated.
    unavailable_percent: float


class Playlist(BaseModel):
    progress: PlaybackProgress
    tracks: list[AudioTrack]
