from fastapi import APIRouter, HTTPException

from api import get_logger
from api.models import api
from api.services.sections import SectionServiceDep

LOG = get_logger(__name__)

sections_router = APIRouter()


@sections_router.post("/{section_id}")
def update_section(section_id: int,
                   api_section: api.BookSection,
                   section_service: SectionServiceDep):
    if not section_service.set_content(section_id, api_section.content):
        raise HTTPException(status_code=404, detail="Section not found")


@sections_router.delete("/{section_id}", status_code=204)
def delete_section(section_id: int, section_service: SectionServiceDep):
    if not section_service.delete_sections(section_ids=[section_id]):
        raise HTTPException(status_code=404, detail="Section not found")
