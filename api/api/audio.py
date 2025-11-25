from typing import Set

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from api import SessionDep
from api.models import db
from api.services.audiotracks import AudioTrackService

audio_router = APIRouter()

@audio_router.post("/generate")
def generate_speech(sections: Set[int],
                    session: SessionDep,
                    audio_track_service: AudioTrackService = Depends()):

    stmt = (select(db.Section)
            .where(db.Section.id.in_(sections))
            .order_by(db.Section.section_index))
    db_sections = session.execute(stmt).scalars().all()

    for section in db_sections:
        sections.remove(section.id)

    if sections:
        raise HTTPException(status_code=404, detail=f"Sections {sections} not found")

    audio_track_service.generate_speech(db_sections)
