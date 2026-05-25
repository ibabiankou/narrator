import logging
import uuid
from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile
from sqlalchemy.exc import NoResultFound

from api.models import api, domain
from api.models.api import SetCover
from api.models.auth import UserDep
from api.services.books import BookServiceDep
from api.services.files import FilesServiceDep
from api.utils.imgproxy import ImgProxy

LOG = logging.getLogger(__name__)

metadata_router = APIRouter(tags=["Metadata API"])


@metadata_router.post("/cover")
def set_book_cover(book_id: uuid.UUID,
                   request: SetCover,
                   user: UserDep,
                   book_service: BookServiceDep):
    is_owner = book_service.is_owner(user.id, book_id)
    if is_owner is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if not is_owner and not user.has_any_role(["admin"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    img_proxy = ImgProxy()

    cover_file = request.file_path
    if not img_proxy.is_img_proxy_url(request.file_path):
        cover_file = img_proxy.build_url(request.file_path)

    book_service.set_cover(book_id, cover_file)


@metadata_router.post("/upload-cover")
def upload_book_cover(book_id: uuid.UUID,
                      file: UploadFile,
                      user: UserDep,
                      book_service: BookServiceDep,
                      file_service: FilesServiceDep) -> str:
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. The limit is 5MB.")

    is_owner = book_service.is_owner(user.id, book_id)
    if is_owner is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if not is_owner and not user.has_any_role(["admin"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    file_key = f"{book_id}/images/covers/{file.filename}"
    file_bytes = BytesIO(file.file.read())
    file_service.upload_file(file_key, file_bytes)

    img_proxy = ImgProxy()
    thumbnail_path = img_proxy.build_url(file_key)

    book_service.set_cover(book_id, thumbnail_path)
    return thumbnail_path


@metadata_router.get("/review")
def get_book_metadata_for_review(
        book_id: uuid.UUID,
        user: UserDep,
        book_service: BookServiceDep) -> api.BookMetadataForReview:
    try:
        return book_service.metadata_for_review(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")


@metadata_router.post("/review")
def update_book_metadata(
        book_id: uuid.UUID,
        metadata: domain.BookMetadata,
        user: UserDep,
        book_service: BookServiceDep) -> api.BookOverview:
    try:
        return book_service.update_metadata(book_id, metadata)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")
