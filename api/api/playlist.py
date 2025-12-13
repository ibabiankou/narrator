import uuid
from typing import Set, Optional

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select

from api import get_logger, SessionDep
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

    progress = _progress(*progress_service.get_progress(book_id))
    return api.Playlist(progress=progress, tracks=ready_tracks)


def _progress(playback_progress, stats):
    section_id = playback_progress.section_id if playback_progress else None
    section_progress = playback_progress.section_progress if playback_progress else None

    global_progress_seconds = stats["played_duration"] + section_progress or 0
    total_duration = stats["narrated_duration"]

    # Percentage here is calculated based on the length of narrated sections
    available_percent = stats["available"] / stats["total"] * 100
    unavailable_percent = stats["missing"] / stats["total"] * 100
    queued_percent = stats["queued"] / stats["total"] * 100

    return api.PlaybackProgress(
        section_id=section_id,
        section_progress_seconds=section_progress,
        global_progress_seconds=global_progress_seconds,
        total_narrated_seconds=total_duration,
        available_percent=available_percent,
        queued_percent=queued_percent,
        unavailable_percent=unavailable_percent
    )

@playlists_router.post("/{book_id}/progress")
def update_progress(request: api.PlaybackProgressUpdate,
                    progress_service: PlaybackProgressService = Depends()):
    upsert = db.PlaybackProgress(book_id=request.book_id,
                                 section_id=request.section_id,
                                 section_progress=request.section_progress_seconds)
    progress_service.upsert_progress(upsert)


@playlists_router.post("/{book_id}/generate")
def generate_speech(book_id: uuid.UUID,
                    sections: Optional[Set[int]],
                    limit: Optional[int],
                    session: SessionDep,
                    audio_track_service: AudioTrackService = Depends(),
                    progress_service: PlaybackProgressService = Depends()
                    ) -> api.Playlist:

    if not sections and not limit:
        raise HTTPException(status_code=400, detail="Either sections or limit must be provided")
    if sections and limit:
        raise HTTPException(status_code=400, detail="Only one of sections or limit can be provided")

    if sections:
        stmt = (select(db.Section)
                .where(db.Section.id.in_(sections))
                .order_by(db.Section.section_index))
        db_sections = session.execute(stmt).scalars().all()

        # Ensure all sections exist.
        for section in db_sections:
            sections.remove(section.id)

        if sections:
            raise HTTPException(status_code=404, detail=f"Sections {sections} not found")
    else:
        stmt = (select(db.Section).outerjoin(db.AudioTrack, db.Section.id == db.AudioTrack.section_id)
                .where(db.AudioTrack.id.is_(None), db.Section.book_id == book_id)
                .order_by(db.Section.section_index).limit(limit))

        db_sections = session.execute(stmt).scalars().all()

    new_tracks = [
        api.AudioTrack(book_id=track.book_id,
                       section_id=track.section_id,
                       status=track.status,
                       file_name=track.file_name,
                       duration=track.duration)
        for track in audio_track_service.generate_speech(db_sections)
    ]
    progress = _progress(*progress_service.get_progress(book_id))
    return api.Playlist(progress=progress, tracks=new_tracks)
