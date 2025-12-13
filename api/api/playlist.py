import uuid

from fastapi import APIRouter
from fastapi.params import Depends

from api import get_logger
from api.models import db, api
from api.services.audiotracks import AudioTrackService
from api.services.progress import PlaybackProgressService

LOG = get_logger(__name__)

playlists_router = APIRouter()


@playlists_router.get("/{book_id}")
def get_playlist(book_id: uuid.UUID,
                 audiotrack_service: AudioTrackService = Depends(),
                 progress_service: PlaybackProgressService = Depends()
                 ) -> api.Playlist:
    # Read all the audio tracks for this book. Gives us ready and queued sections
    ready_tracks = [
        api.AudioTrack(book_id=track.book_id,
                       section_id=track.section_id,
                       status=track.status,
                       file_name=track.file_name,
                       duration=track.duration)
        for track in audiotrack_service.get_tracks(book_id)
        if track.status == db.AudioStatus.ready
    ]

    playback_progress, stats = progress_service.get_progress(book_id)
    section_id = playback_progress.section_id if playback_progress else None
    section_progress = playback_progress.section_progress if playback_progress else None

    global_progress_seconds = 0
    if section_id and section_progress:
        for track in ready_tracks:
            if track.section_id == section_id:
                global_progress_seconds += section_progress
                break
            global_progress_seconds += track.duration
    total_duration = sum([track.duration for track in ready_tracks])

    # Percentage here is calculated based on the length of narrated sections
    available_percent = stats["available"] / stats["total"] * 100
    unavailable_percent = stats["missing"] / stats["total"] * 100
    queued_percent = stats["queued"] / stats["total"] * 100

    progress = api.PlaybackProgress(
        section_id=section_id,
        section_progress_seconds=section_progress,
        global_progress_seconds=global_progress_seconds,
        total_narrated_seconds=total_duration,
        available_percent=available_percent,
        queued_percent=queued_percent,
        unavailable_percent=unavailable_percent
    )

    return api.Playlist(progress=progress, tracks=ready_tracks)


@playlists_router.post("/{book_id}/progress")
def update_progress(request: api.PlaybackProgressUpdate,
                    progress_service: PlaybackProgressService = Depends()):
    upsert = db.PlaybackProgress(book_id=request.book_id,
                                 section_id=request.section_id,
                                 section_progress=request.section_progress_seconds)
    progress_service.upsert_progress(upsert)
