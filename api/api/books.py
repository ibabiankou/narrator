import logging
import uuid
from io import BytesIO
from typing import List

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response, Depends, UploadFile
from sqlalchemy.exc import NoResultFound

from api.models import db, api
from api.models.auth import UserDep
from api.services.books import BookServiceDep
from api.services.files import FilesServiceDep
from api.services.progress import PlaybackProgressServiceDep

LOG = logging.getLogger(__name__)

books_router = APIRouter(tags=["Books API"])


@books_router.post("/")
def create_book(file: UploadFile,
                user: UserDep,
                book_service: BookServiceDep,
                background_tasks: BackgroundTasks) -> api.BookOverview:
    if file.size > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    return book_service.create_book(user.id, file.filename, BytesIO(file.file.read()), background_tasks)


@books_router.post("/{book_id}/narrate")
def narrate_book(book_id: uuid.UUID,
                 request: List[api.TableOfContentsItem],
                 user: UserDep,
                 book_service: BookServiceDep):
    is_owner = book_service.is_owner(user.id, book_id)
    if is_owner is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if not is_owner and not user.has_any_role(["admin"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    book_service.narrate_book(book_id, request)


@books_router.get("/")
def list_books(
        user: UserDep,
        book_service: BookServiceDep,
        page_request: api.PageRequest = Depends()
) -> api.PagedResponse[api.BookOverview]:
    return book_service.list_books(user.id, page_request)


@books_router.get("/search")
def search_books(
        query: str,
        user: UserDep,
        book_service: BookServiceDep,
        page_request: api.PageRequest = Depends()
) -> api.PagedResponse[api.BookOverview]:
    return book_service.search_books(user.id, query, page_request)


@books_router.get("/{book_id}/details")
def get_book_details(book_id: uuid.UUID,
                     book_service: BookServiceDep,
                     ) -> api.BookDetails:
    try:
        return book_service.get_book_details(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")


@books_router.get("/{book_id}/table-of-contents")
def get_table_of_contents(book_id: uuid.UUID,
                          book_service: BookServiceDep,
                          ) -> List[api.TableOfContentsItem]:
    try:
        return book_service.get_table_of_contents(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")


@books_router.get("/{book_id}/images")
def list_images(book_id: uuid.UUID, file_service: FilesServiceDep) -> list[str]:
    return file_service.list_files(f"{book_id}/images")


@books_router.delete("/{book_id}", status_code=204)
def delete_book(book_id: uuid.UUID,
                user: UserDep,
                book_service: BookServiceDep):
    is_owner = book_service.is_owner(user.id, book_id)
    if is_owner is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if not is_owner and not user.has_any_role(["admin"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        book_service.delete_book(user.id, book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")


@books_router.get("/{book_id}/playback_info")
def get_playback_info(book_id: uuid.UUID,
                      user: UserDep,
                      progress_service: PlaybackProgressServiceDep) -> api.PlaybackInfo:
    return progress_service.get_playback_info(user.id, book_id)


@books_router.post("/{book_id}/playback_info")
def update_playback_info(request: api.PlaybackInfo,
                         user: UserDep,
                         progress_service: PlaybackProgressServiceDep):
    progress_service.upsert_progress(db.PlaybackProgress(user_id=user.id, book_id=request.book_id, data=request.data))
    return Response(status_code=201)
