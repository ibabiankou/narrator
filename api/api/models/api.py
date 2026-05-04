import uuid
from typing import Optional, Generic, List, TypeVar

from fastapi import Query
from pydantic import BaseModel

from api.models import db
from api.models.domain import BookMetadata, MetadataCandidates

T = TypeVar("T")


class CreateBookRequest(BaseModel):
    id: uuid.UUID
    title: str
    pdf_temp_file_id: uuid.UUID


class PageRequest(BaseModel):
    page_index: int = Query(0, ge=0, description="Page index")
    size: int = Query(25, ge=1, le=100, description="Items per page")


class PageInfo(BaseModel):
    total: int
    index: int
    size: int


class PagedResponse(BaseModel, Generic[T]):
    items: List[T]
    page_info: PageInfo


def paged_response(items: List[T], total: int, index: int, size: int) -> PagedResponse[T]:
    return PagedResponse(items=items, page_info=PageInfo(total=total, index=index, size=size))


class BookOverview(BookMetadata):
    id: uuid.UUID
    owner_id: uuid.UUID
    pdf_file_name: str
    number_of_pages: Optional[int] = None
    status: str

    @classmethod
    def from_orm(cls, book: db.Book):
        return BookOverview(id=book.id,
                            owner_id=book.owner_id,
                            pdf_file_name=book.file_name,
                            number_of_pages=book.number_of_pages,
                            status=book.status,
                            cover=book.cover,
                            title=book.title,
                            series=book.series,
                            description=book.description,
                            authors=[] if book.authors is None else list(book.authors),
                            isbns=[] if book.isbns is None else list(book.isbns))


class BookMetadataForReview(BaseModel):
    overview: BookOverview
    metadata_candidates: MetadataCandidates


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
