import logging
import uuid

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
    for dir_name in dirs:
        LOG.info("Found dir %s", dir_name)
        try:
            book_service.get_book(uuid.UUID(dir_name))
        except NoResultFound:
            LOG.warning("Book with ID %s not found. Deleting dir %s.", dir_name, dir_name)
            if cleanup:
                files_service.delete_book_files(dir_name)
