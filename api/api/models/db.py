import datetime
import os
import uuid
from enum import StrEnum
from typing import Optional, Type, List

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, ForeignKey, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
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


class BookStatus(StrEnum):
    processing = "processing"
    ready_for_metadata_review = "ready_for_metadata_review"
    ready = "ready"


class MetadataCandidate(BaseModel):
    source: str = Field(description="The source of the metadata.")
    title: Optional[str] = Field(description="The full title of the book.")
    series: Optional[str] = Field(description="The name of the series.")
    authors: List[str] = Field(description="A list of authors of the book.")
    isbn: List[str] = Field(description="The 10 or 13-digit ISBN(s) if found in the text.")


class MetadataCandidates(BaseModel):
    candidates: list[MetadataCandidate]
    preferred_index: int = Field(description="Zero based index of the candidate we think to be the best.")
    selected_index: Optional[str] = Field(description="Zero based index of the candidate selected by the user.")


class Book(Base):
    __tablename__ = "books"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    owner_id: Mapped[uuid.UUID]
    title: Mapped[str]
    file_name: Mapped[str]
    number_of_pages: Mapped[Optional[int]]
    created_time: Mapped[datetime.datetime]
    status: Mapped[str]
    cover: Mapped[Optional[str]]

    metadata_candidates: Mapped[Optional[MetadataCandidates]] = mapped_column(type_=PydanticType(MetadataCandidates))

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
