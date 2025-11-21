from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from api import SessionDep, get_logger
from api.models import db, api
from api.models.api import GenerateSpeechMode
from api.services.sections import SectionService

LOG = get_logger(__name__)

sections_router = APIRouter()


@sections_router.post("/{section_id}")
def update_section(section_id: int,
                   api_section: api.BookSection,
                   session: SessionDep):
    db_section = session.get(db.Section, section_id)
    if db_section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    db_section.content = api_section.content
    # TODO: consider if other fields should be updated as well
    session.commit()


@sections_router.delete("/{section_id}", status_code=204)
def delete_section(section_id: int, session: SessionDep):
    section = session.get(db.Section, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    session.delete(section)
    session.commit()


@sections_router.post("/{section_id}/generate-speech")
def generate_speech(section_id: int,
                    request: api.GenerateSpeechRequest,
                    session: SessionDep,
                    section_service: SectionService = Depends()):
    sections = []

    section = session.get(db.Section, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    if request.mode == GenerateSpeechMode.single:
        sections.append(section)
    elif request.mode == GenerateSpeechMode.all_missing_before:
        stmt = (session.query(db.Section)
                .where(db.Section.book_id == section.book_id)
                .where(db.Section.section_index <= section.section_index)
                .where(db.Section.speech_status == db.SpeechStatus.missing))
        sections = session.execute(stmt).scalars().all()
    else:
        raise HTTPException(status_code=400, detail="Unknown speech generation mode")

    section_service.generate_speech(sections)
