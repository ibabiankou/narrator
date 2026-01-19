import uuid

import m3u8
from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, NoResultFound

from api import SessionDep, get_logger
from api.models import db, api
from api.services.audiotracks import AudioTrackServiceDep
from api.services.books import BookServiceDep
from api.services.progress import PlaybackProgressServiceDep
from api.services.sections import SectionServiceDep

LOG = get_logger(__name__)

books_router = APIRouter(tags=["Books API"])


@books_router.post("/")
def create_book(book: api.CreateBookRequest,
                background_tasks: BackgroundTasks,
                book_service: BookServiceDep) -> api.BookOverview:
    try:
        book = book_service.create_book(book)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Book with this title already exists")

    # Process the book in the background
    background_tasks.add_task(book_service.split_pages, book.id, book.pdf_file_name)
    background_tasks.add_task(book_service.extract_text, book.id, book.pdf_file_name)

    return book


@books_router.get("/")
def list_books(session: SessionDep) -> list[api.BookOverview]:
    # Read books from DB ordered by the date they added.
    stmt = select(db.Book).order_by(db.Book.created_time.desc(), db.Book.title)
    books = session.execute(stmt).scalars().all()

    resp = []
    for book in books:
        resp.append(api.BookOverview(id=book.id,
                                     title=book.title,
                                     pdf_file_name=book.file_name,
                                     number_of_pages=book.number_of_pages,
                                     status=book.status))

    return resp


def get_book_pages(book: db.Book, section_svc: SectionServiceDep) -> list[api.BookPage]:
    if book.status != db.BookStatus.ready or book.number_of_pages is None:
        # There will be no content, so return immediately.
        return []

    # Convert into the API model.
    pages = []
    pages_dict = {}
    # For now, I simply generate pages, but I might need to store that data explicitly instead.
    for i in range(book.number_of_pages or 0):
        pages.append(api.BookPage(index=i, file_name=f"{i}.pdf", sections=[]))
        pages_dict[i] = pages[-1]

    db_sections = section_svc.get_sections(book.id)
    for section in db_sections:
        book_section = api.BookSection(id=section.id,
                                       book_id=section.book_id,
                                       page_index=section.page_index,
                                       section_index=section.section_index,
                                       content=section.content)
        pages_dict[section.page_index].sections.append(book_section)
    return pages


@books_router.get("/{book_id}")
def get_book_with_content(book_id: uuid.UUID,
                          book_service: BookServiceDep,
                          section_svc: SectionServiceDep
                          ) -> api.BookWithContent:
    try:
        book = book_service.get_book(book_id)
        overview = api.BookOverview(id=book.id,
                                    title=book.title,
                                    pdf_file_name=book.file_name,
                                    number_of_pages=book.number_of_pages,
                                    status=book.status)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")

    raw_stats = book_service.get_stats(book_id)
    total = raw_stats.get("total")
    stats = api.BookStats(total_narrated_seconds=raw_stats.get("narrated_duration"),
                          available_percent=(raw_stats.get("available") / total if total > 0 else 1) * 100)
    pages = get_book_pages(book, section_svc)

    return api.BookWithContent(overview=overview, stats=stats, pages=pages)


@books_router.delete("/{book_id}", status_code=204)
def delete_book(book_id: uuid.UUID, book_service: BookServiceDep):
    try:
        book_service.delete_book(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")


@books_router.post("/{book_id}/reprocess")
def reprocess_book(book_id: uuid.UUID,
                   session: SessionDep,
                   background_tasks: BackgroundTasks,
                   book_service: BookServiceDep,
                   section_service: SectionServiceDep):
    book = session.get(db.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    session.execute(update(db.Book).where(db.Book.id == book.id).values(status=db.BookStatus.processing))
    session.commit()

    section_service.delete_sections(book_id=book.id)

    background_tasks.add_task(book_service.extract_text, book.id, book.file_name)


@books_router.get("/{book_id}/m3u8")
def book_playlist(book_id: uuid.UUID,
                  book_service: BookServiceDep,
                  audio_track_service: AudioTrackServiceDep):
    try:
        book_service.get_book(book_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Book not found")

    all_tracks = audio_track_service.get_tracks(book_id)
    ready_tracks = [t for t in all_tracks if t.status == db.AudioStatus.ready]

    LOG.info("Loaded %s tracks", len(ready_tracks))

    return Response(
        content=generate_dynamic_playlist(ready_tracks),
        media_type="application/vnd.apple.mpegurl"
    )


def generate_dynamic_playlist(tracks: list[db.AudioTrack]):

    playlist = m3u8.M3U8()

    playlist.version = "4"
    playlist.target_duration = max([t.duration for t in tracks] or [0]) + 1
    playlist.media_sequence = 0
    # TODO: What would be behavior if I set it to False? Would it help for books that are being generated?
    playlist.is_endlist = True

    for track in tracks:
        segment = m3u8.Segment(
            uri=f"/api/files/{track.book_id}/speech/{track.file_name}",
            duration=track.duration,
            discontinuity=True,
            dateranges=[{
                "id": str(track.section_id),
                "start_date": "1111-11-11",
                "x_order": str(track.playlist_order),
                "x_duration": str(track.duration)
            }]
        )
        playlist.segments.append(segment)

    return playlist.dumps()


@books_router.get("/{book_id}/playback_info")
def get_playback_info(book_id: uuid.UUID, progress_service: PlaybackProgressServiceDep) -> api.PlaybackInfo:
    playback_info = progress_service.get_playback_info(book_id)
    return api.PlaybackInfo(book_id=book_id, data=playback_info.data if playback_info else {})


@books_router.post("/{book_id}/playback_info")
def update_playback_info(request: api.PlaybackInfo,
                         book_id: uuid.UUID,
                         progress_service: PlaybackProgressServiceDep):
    progress_service.upsert_progress(db.PlaybackProgress(book_id=request.book_id, data=request.data))
    return Response(status_code=201)
