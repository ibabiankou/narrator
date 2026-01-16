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


class AudioTrack(BaseModel):
    book_id: uuid.UUID
    section_id: int
    status: str
    file_name: Optional[str]
    duration: Optional[float]


class PlaybackProgress(BaseModel):
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

    # Whether to scroll to the currently playing section.
    sync_current_section: bool

    playback_rate: float


EMPTY_PLAYBACK_PROGRESS = PlaybackProgress(
    section_id=None,
    section_progress_seconds=None,
    global_progress_seconds=0,
    total_narrated_seconds=0,
    available_percent=0,
    queued_percent=0,
    unavailable_percent=0,
    sync_current_section=False,
    playback_rate=1
)


class PlaybackStateUpdate(BaseModel):
    book_id: uuid.UUID
    data: dict


class Playlist(BaseModel):
    progress: PlaybackProgress
    tracks: list[AudioTrack]

EMPTY_PLAYLIST = Playlist(progress=EMPTY_PLAYBACK_PROGRESS, tracks=[])
