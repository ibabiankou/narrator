import datetime
import os
import uuid
from enum import StrEnum
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

load_dotenv()
pg_url = os.path.expandvars(os.getenv("PG_URL"))
engine = create_engine(pg_url, pool_recycle=600)
DbSession = sessionmaker(engine)

def get_session():
    with Session(engine) as session:
        yield session

class Base(DeclarativeBase):
    pass


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
