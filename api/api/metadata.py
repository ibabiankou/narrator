import logging
import uuid
from io import BytesIO

from fastapi import APIRouter, HTTPException

from api.models.api import SetCover
from api.models.auth import UserDep
from api.services.books import BookServiceDep
from api.services.files import FilesServiceDep
from api.utils.images import create_thumbnail

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
    file_data = file_service._get_object(request.file_path)
    thumbnail_buffer = create_thumbnail(BytesIO(file_data.body))
    thumbnail_path = f"{book_id}/images/cover.webp"
    file_service.upload_file(thumbnail_path, thumbnail_buffer)

    book_service.set_cover(book_id, thumbnail_path)
