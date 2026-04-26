import datetime
import os
import uuid
from enum import StrEnum
from functools import total_ordering
from typing import Optional, Type, List

from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy import create_engine, ForeignKey, TypeDecorator, String
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

from api.models import domain

load_dotenv()
pg_url = os.path.expandvars(os.getenv("PG_URL"))
engine = create_engine(pg_url, pool_recycle=600)
DbSession = sessionmaker(engine)


class Base(DeclarativeBase):
    def as_dict(self):
        return {
            c.key: getattr(self, c.key)
            for c in self.__mapper__.columns
            if not c.primary_key
        }


class PydanticType(TypeDecorator):
    """Serializes a single Pydantic model (and its nested data) to JSONB."""
    impl = JSONB

    def __init__(self, pydantic_type: Type[BaseModel], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pydantic_type = pydantic_type

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.model_dump() if isinstance(value, BaseModel) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.pydantic_type.model_validate(value)


class TempFile(Base):
    __tablename__ = "temp_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    file_name: Mapped[str]
    file_path: Mapped[str]
    upload_time: Mapped[datetime.datetime]


@total_ordering
class BookStatus(StrEnum):
    # Just uploaded book is going through initial processing.
    processing = "processing"

    # Initial processing is done, and the book is ready for metadata review.
    ready_for_metadata_review = "ready_for_metadata_review"

    # Book metadata is reviewed, so it's time to review the content extracted from the PDF.
    ready_for_content_review = "ready_for_content_review"

    # The book is ready to be narrated, but waiting in the queue.
    queued = "queued"

    # The book is being narrated.
    narrating = "narrating"

    # The book is fully narrated and ready for playback or download.
    ready = "ready"

    def _get_rank(self):
        ordered = list(BookStatus)
        return ordered.index(self)

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self._get_rank() < other._get_rank()
        return NotImplemented


class Book(Base):
    __tablename__ = "books"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    owner_id: Mapped[uuid.UUID]
    file_name: Mapped[str]
    number_of_pages: Mapped[Optional[int]]
    created_time: Mapped[datetime.datetime]
    status: Mapped[str]

    cover: Mapped[Optional[str]]
    title: Mapped[Optional[str]]
    series: Mapped[Optional[str]]
    description: Mapped[Optional[str]]
    authors: Mapped[List[str]] = mapped_column(type_=ARRAY(String))
    isbns: Mapped[List[str]] = mapped_column(type_=ARRAY(String))

    metadata_candidates: Mapped[Optional[domain.MetadataCandidates]] = mapped_column(
        type_=PydanticType(domain.MetadataCandidates))

    # TODO: Add errors field. JSONB array of dictionaries. Any processing / validation errors encountered
    #  should be stored there and displayed in UI.


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id"))

    page_index: Mapped[int]
    section_index: Mapped[int]

    content: Mapped[str]
    phonemes: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return (f"Section(id={self.id}, book_id={self.book_id}, page_index={self.page_index}, "
                f"section_index={self.section_index}")


class AudioStatus(StrEnum):
    missing = "missing"
    queued = "queued"
    generating = "generating"
    failed = "failed"
    ready = "ready"


class AudioTrack(Base):
    __tablename__ = "audio_tracks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id"))
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    playlist_order: Mapped[int]

    status: Mapped[str] = mapped_column(default=AudioStatus.missing.value)
    file_name: Mapped[Optional[str]]

    duration: Mapped[Optional[float]]
    bytes: Mapped[Optional[int]]


class PlaybackProgress(Base):
    __tablename__ = "playback_progress"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID]
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id"))

    data: Mapped[dict] = mapped_column(type_=JSONB)


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID]
    # One of: system, user_preferences
    kind: Mapped[str]

    data: Mapped[dict] = mapped_column(type_=JSONB)
