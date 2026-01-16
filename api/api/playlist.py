import uuid
from typing import Set, Optional, Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Query
from sqlalchemy import select

from api import get_logger, SessionDep
from api.models import db, api
from api.models.api import EMPTY_PLAYLIST
from api.services.audiotracks import AudioTrackServiceDep
from api.services.progress import PlaybackProgressServiceDep, ProgressData

LOG = get_logger(__name__)

playlists_router = APIRouter()


@playlists_router.get("/{book_id}")
def get_playlist(book_id: uuid.UUID,
                 audiotrack_service: AudioTrackServiceDep,
                 progress_service: PlaybackProgressServiceDep
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

    data = progress_service.get_progress(book_id)
    if data is None:
        return EMPTY_PLAYLIST
    else:
        return api.Playlist(progress=_progress(data), tracks=ready_tracks)


def _progress(data: ProgressData):
    # TODO: Think how to handle this shit better.
    playback_progress = data.playback_progress or db.PlaybackProgress(book_id=uuid.uuid4(), data={})
    stats = data.stats
    sync_current_section = playback_progress.data.get("sync_current_section") or True
    playback_rate = playback_progress.data.get("playback_rate") or 1.0

    global_progress_seconds = playback_progress.data.get("progress_seconds") or 0
    total_duration = stats["narrated_duration"]

    # Percentage here is calculated based on the length of narrated sections
    available_percent = stats["available"] / stats["total"] * 100
    unavailable_percent = stats["missing"] / stats["total"] * 100
    queued_percent = stats["queued"] / stats["total"] * 100

    return api.PlaybackProgress(
        global_progress_seconds=global_progress_seconds,
        total_narrated_seconds=total_duration,
        available_percent=available_percent,
        queued_percent=queued_percent,
        unavailable_percent=unavailable_percent,
        sync_current_section=sync_current_section,
        playback_rate=playback_rate
    )


@playlists_router.post("/{book_id}/progress")
def update_progress(request: api.PlaybackStateUpdate,
                    progress_service: PlaybackProgressServiceDep):
    upsert = db.PlaybackProgress(book_id=request.book_id, data=request.data)
    progress_service.upsert_progress(upsert)


@playlists_router.post("/{book_id}/generate")
def generate_speech(book_id: uuid.UUID,
                    sections: Optional[Set[int]],
                    session: SessionDep,
                    audio_track_service: AudioTrackServiceDep,
                    progress_service: PlaybackProgressServiceDep,
                    limit: Optional[int] = None
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

    if not db_sections:
        LOG.info("No sections found to generate speech for")
        new_tracks = []
    else:
        new_tracks = audio_track_service.generate_speech(db_sections)

    data = progress_service.get_progress(book_id)
    if data is None:
        return EMPTY_PLAYLIST
    else:
        return api.Playlist(progress=_progress(data), tracks=new_tracks)


@playlists_router.get("/{book_id}/tracks")
def get_tracks(book_id: uuid.UUID,
               audio_track_service: AudioTrackServiceDep,
               progress_service: PlaybackProgressServiceDep,
               sections: Annotated[Set[int], Query()] = None
               ) -> api.Playlist:
    tracks = [
        api.AudioTrack(book_id=track.book_id,
                       section_id=track.section_id,
                       status=track.status,
                       file_name=track.file_name,
                       duration=track.duration)
        for track in audio_track_service.get_tracks(book_id, sections)
    ]

    data = progress_service.get_progress(book_id)
    if data is None:
        return EMPTY_PLAYLIST
    else:
        return api.Playlist(progress=_progress(data), tracks=tracks)
