from fastapi import APIRouter, HTTPException

from api import get_logger
from api.models import api
from api.models.auth import UserDep
from api.services.audiotracks import AudioTrackServiceDep
from api.services.sections import SectionServiceDep

LOG = get_logger(__name__)

sections_router = APIRouter(tags=["Sections API"])


@sections_router.post("/{section_id}")
def update_section(section_id: int,
                   user: UserDep,
                   api_section: api.BookSection,
                   section_service: SectionServiceDep):
    if not section_service.is_owner(user.id, section_id) and not user.has_any_role(["admin"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if not section_service.set_content(section_id, api_section.content):
        raise HTTPException(status_code=404, detail="Section not found")


@sections_router.post("/{section_id}/re-narrate")
def renarrate(section_id: int,
              user: UserDep,
              section_service: SectionServiceDep,
              audiotracks_service: AudioTrackServiceDep):
    if not section_service.is_owner(user.id, section_id) and not user.has_any_role(["admin"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    section = section_service.get_section(section_id)

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    audiotracks_service.generate_speech([section])


@sections_router.delete("/{section_id}", status_code=204)
def delete_section(section_id: int, user: UserDep, section_service: SectionServiceDep):
    if not section_service.is_owner(user.id, section_id) and not user.has_any_role(["admin"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if not section_service.delete_sections(section_ids=[section_id]):
        raise HTTPException(status_code=404, detail="Section not found")
