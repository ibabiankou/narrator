import datetime
import os
import uuid
from enum import StrEnum
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, ForeignKey, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

load_dotenv()
pg_url = os.path.expandvars(os.getenv("PG_URL"))
engine = create_engine(pg_url, pool_recycle=600)
DbSession = sessionmaker(engine)


def get_session():
    with Session(engine) as session:
        yield session


class Base(DeclarativeBase):
    def as_dict(self):
        return {
            c.key: getattr(self, c.key)
            for c in self.__mapper__.columns
            if not c.primary_key
        }


class TempFile(Base):
    __tablename__ = "temp_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    file_name: Mapped[str]
    file_path: Mapped[str]
    upload_time: Mapped[datetime.datetime]


class BookStatus(StrEnum):
    processing = "processing"
    ready = "ready"


class Book(Base):
    __tablename__ = "books"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    title: Mapped[str]
    file_name: Mapped[str]
    number_of_pages: Mapped[Optional[int]]
    created_time: Mapped[datetime.datetime]
    status: Mapped[str]


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


class PlaybackProgress(Base):
    __tablename__ = "playback_progress"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id"), unique=True)

    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    section_progress: Mapped[Optional[float]]
