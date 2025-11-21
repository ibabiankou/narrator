from fastapi import APIRouter, HTTPException

from api import SessionDep, get_logger
from api.models import db, api

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
