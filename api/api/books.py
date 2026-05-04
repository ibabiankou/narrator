import logging
import uuid
from io import BytesIO

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response, Depends, UploadFile
from sqlalchemy.exc import NoResultFound

from api.models import db, api
from api.models.auth import UserDep
from api.services.audiotracks import AudioTrackServiceDep
from api.services.books import BookServiceDep
from api.services.files import FilesServiceDep
from api.services.progress import PlaybackProgressServiceDep
from api.services.sections import SectionServiceDep

LOG = logging.getLogger(__name__)

books_router = APIRouter(tags=["Books API"])


@books_router.post("/add-book")
def create_book_v2(file: UploadFile,
                   user: UserDep,
                   book_service: BookServiceDep,
                   background_tasks: BackgroundTasks) -> api.BookOverview:
    if file.size > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    return book_service.create_book_v2(user.id, file.filename, BytesIO(file.file.read()), background_tasks)


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


def get_book_pages(book_id, number_of_pages: int, section_svc: SectionServiceDep) -> list[api.BookPage]:
    # Convert into the API model.
    pages = []
    pages_dict = {}
    # For now, I simply generate pages, but I might need to store that data explicitly instead.
    for i in range(number_of_pages or 0):
        pages.append(api.BookPage(index=i, file_name=f"{i}.pdf", sections=[]))
        pages_dict[i] = pages[-1]

    sections = section_svc.get_sections(book_id)
    for section in sections:
        pages_dict[section.page_index].sections.append(section)
    return pages


@books_router.get("/{book_id}")
def get_book_with_content(book_id: uuid.UUID,
                          book_service: BookServiceDep,
                          section_svc: SectionServiceDep
                          ) -> api.BookWithContent:
    try:
        overview = book_service.get_book_overview(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")

    raw_stats = book_service.get_stats(book_id)
    total = raw_stats.get("total")
    stats = api.BookStats(total_narrated_seconds=raw_stats.get("narrated_duration"),
                          available_percent=(raw_stats.get("available") / total if total > 0 else 1) * 100,
                          total_size_bytes=raw_stats.get("total_size_bytes"))
    pages = get_book_pages(overview.id, overview.number_of_pages, section_svc)

    return api.BookWithContent(overview=overview, stats=stats, pages=pages)


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


@books_router.get("/{book_id}/m3u8")
def book_playlist(book_id: uuid.UUID,
                  book_service: BookServiceDep,
                  audio_track_service: AudioTrackServiceDep):
    try:
        book_service.get_book(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")

    return Response(
        content=audio_track_service.get_playlist(book_id),
        media_type="application/vnd.apple.mpegurl"
    )


@books_router.get("/{book_id}/playback_info")
def get_playback_info(book_id: uuid.UUID,
                      user: UserDep,
                      progress_service: PlaybackProgressServiceDep) -> api.PlaybackInfo:
    return progress_service.get_playback_info(user.id, book_id)


@books_router.post("/{book_id}/playback_info")
def update_playback_info(request: api.PlaybackInfo,
                         book_id: uuid.UUID,
                         user: UserDep,
                         progress_service: PlaybackProgressServiceDep):
    progress_service.upsert_progress(db.PlaybackProgress(user_id=user.id, book_id=request.book_id, data=request.data))
    return Response(status_code=201)


@books_router.post("/{book_id}/enqueue")
def enqueue_book_for_narration(book_id: uuid.UUID,
                               user: UserDep,
                               book_service: BookServiceDep):
    try:
        book_overview = book_service.get_book_overview(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")

    if book_overview.status != db.BookStatus.ready_for_content_review:
        raise HTTPException(status_code=422, detail="Only books ready for content review can be enqueued.")

    book_service.update_status(book_id, db.BookStatus.queued)
    return Response(status_code=204)
