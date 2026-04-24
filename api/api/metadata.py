import logging
import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import NoResultFound

from api.models import api, domain
from api.models.api import SetCover
from api.models.auth import UserDep
from api.services.books import BookServiceDep
from api.services.files import FilesServiceDep

LOG = logging.getLogger(__name__)

metadata_router = APIRouter(tags=["Metadata API"])


@metadata_router.post("/cover")
def set_book_cover(book_id: uuid.UUID,
                   request: SetCover,
                   user: UserDep,
                   book_service: BookServiceDep,
                   file_service: FilesServiceDep):
    is_owner = book_service.is_owner(user.id, book_id)
    if is_owner is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if not is_owner and not user.has_any_role(["admin"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Create and store cover thumbnail.
    thumbnail_path = file_service.create_thumbnail(book_id, request.file_path)
    book_service.set_cover(book_id, thumbnail_path)


@metadata_router.get("/review")
def get_book_metadata_for_review(
        book_id: uuid.UUID,
        user: UserDep,
        book_service: BookServiceDep) -> api.BookMetadataForReview:
    try:
        book = book_service.get_book(book_id)
        overview = api.BookOverview.from_orm(book)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")

    return api.BookMetadataForReview(overview=overview, metadata_candidates=book.metadata_candidates)

@metadata_router.post("/review")
def update_book_metadata(
        book_id: uuid.UUID,
        metadata: domain.BookMetadata,
        user: UserDep,
        book_service: BookServiceDep) -> api.BookOverview:
    try:
        book = book_service.update_metadata(book_id, metadata)
        return api.BookOverview.from_orm(book)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")
