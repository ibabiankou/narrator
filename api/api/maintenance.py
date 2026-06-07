import logging
import uuid
from fastapi import APIRouter, Request
from sqlalchemy.exc import NoResultFound

from api.models.auth import AdminUser
from api.services.books import BookServiceDep
from api.services.files import FilesServiceDep
from api.services.narration_queue import NarrationQueueServiceDep

maintenance_router = APIRouter(tags=["Maintenance API"])

LOG = logging.getLogger(__name__)


@maintenance_router.post("/check-orphan-files")
def check_orphan_files(
        user: AdminUser,
        book_service: BookServiceDep,
        files_service: FilesServiceDep,
        prefix: str = None,
        cleanup: bool = False
):
    """Integrity check of files in the object store. Lists all top level directories and checks
     books with corresponding IDs exist. If not, deletes directories.
     Similarly, checks the existence of audio-tracks corresponding to existing speech files."""
    # TODO: Re-evaluate this logic to work with the new setup.

    dirs = files_service.list_dirs(prefix or "")
    LOG.info("Found %s top level directories to check.", len(dirs))
    existing_books = []
    for dir_name in dirs:
        LOG.info("Found dir %s", dir_name)
        try:
            book = book_service.get_book(uuid.UUID(dir_name))
            existing_books.append(book)
        except NoResultFound:
            LOG.info("Book with ID %s not found.", dir_name)
            if cleanup:
                LOG.warning("Deleting dir %s.", dir_name)
                files_service.delete_book_files(dir_name)


@maintenance_router.post("/narrate")
def resend_narration_requests(
        queue_ids: list[int],
        user: AdminUser,
        narration_queue_service: NarrationQueueServiceDep
):
    narration_queue_service.resend(queue_ids)


@maintenance_router.get("/debug-headers")
async def debug_headers(request: Request, admin: AdminUser):
    return {
        "headers": dict(request.headers),
        "client_host": request.client.host,
        "scope_type": request.scope.get("type"),
        "scheme": request.scope.get("scheme"),  # This is what Uvicorn thinks the protocol is
    }
