import logging
import uuid
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy.exc import NoResultFound

from api.models import db
from api.services.audiotracks import AudioTrackServiceDep
from api.services.books import BookServiceDep
from api.services.files import FilesServiceDep

maintenance_router = APIRouter(tags=["Maintenance API"])

LOG = logging.getLogger(__name__)


@maintenance_router.post("/check-audio-tracks")
def check_audio_tracks(
        audio_tracks_service: AudioTrackServiceDep,
        files_service: FilesServiceDep,
        book_id: uuid.UUID = None,
        cleanup: bool = False
):
    """Integrity check of audio files. Loads all audio-tracks and verifies corresponding files
     exist in the object store. If not, then the audio-track is deleted, forcing re-generation."""

    audio_tracks = audio_tracks_service.get_tracks(book_id)
    for track in audio_tracks:
        if track.status != db.AudioStatus.ready:
            continue

        file_key = files_service.speech_filename(track.book_id, track.file_name)
        if not files_service.exists(file_key):
            LOG.warning("Track %s is missing its file %s.", track.id, file_key)
            if cleanup:
                LOG.warning("Deleting track without file: %s", track)
                audio_tracks_service.delete(track.id)


@maintenance_router.post("/check-orphan-files")
def check_orphan_files(
        audio_tracks_service: AudioTrackServiceDep,
        book_service: BookServiceDep,
        files_service: FilesServiceDep,
        prefix: str = None,
        cleanup: bool = False
):
    """Integrity check of files in the object store. Lists all top level directories and checks
     books with corresponding IDs exist. If not, deletes directories.
     Similarly, checks the existence of audio-tracks corresponding to existing speech files."""

    dirs = files_service.list_dirs(prefix or "")
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

    # Now for each existing book, check corresponding audio tracks exist.
    for book in existing_books:
        speech_files = files_service.list_files(str(book.id))
        LOG.info("Checking %s speech files in book %s", len(speech_files), book.id)

        for file in speech_files:
            # TODO: Here I assume file name will always have format [track_id].[ext]
            track_id_str = Path(file).stem

            track_id = int(track_id_str)
            track = audio_tracks_service.get_track(track_id)
            if not track:
                LOG.info("Track %s no longer exist.", track_id)
                if cleanup:
                    LOG.warning("Deleting file %s.", file)
                    files_service.delete_file(file)
