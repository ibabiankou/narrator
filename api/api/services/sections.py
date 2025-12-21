import uuid
from typing import Annotated

from sqlalchemy import delete, update, select

from api import get_logger
from api.models import db
from api.models.db import DbSession
from api.services.audiotracks import AudioTrackServiceDep
from common_lib.service import Service

LOG = get_logger(__name__)


class SectionService(Service):
    def __init__(self, audiotracks_service: AudioTrackServiceDep):
        self.audiotracks_service = audiotracks_service

    def delete_sections(self, book_id: uuid.UUID = None, section_ids: list[int] = None):
        if not book_id and not section_ids:
            raise ValueError("Either book_id or section_ids must be provided")

        # Load the sections to be deleted.
        with DbSession() as session:
            stmt = select(db.Section)
            if book_id:
                stmt = stmt.where(db.Section.book_id == book_id)
            if section_ids:
                stmt = stmt.where(db.Section.id.in_(section_ids))
            sections = session.scalars(stmt).all()

        if not sections:
            return []

        # Delete audio tracks corresponding to the sections being deleted.
        self.audiotracks_service.delete_for_sections(sections)

        # Delete the sections.
        with DbSession() as session:
            stmt = delete(db.Section).returning(db.Section)
            if book_id:
                stmt = stmt.where(db.Section.book_id == book_id)
            if section_ids:
                stmt = stmt.where(db.Section.id.in_(section_ids))
            deleted_sections = session.execute(stmt).scalars().all()
            LOG.info("Deleted %s sections: \n%s", len(deleted_sections), deleted_sections)
            session.commit()

        return deleted_sections

    def set_phonemes(self, section_id: int, phonemes: str):
        with DbSession() as session:
            session.execute(update(db.Section).where(db.Section.id == section_id).values(phonemes=phonemes))
            session.commit()

    def set_content(self, section_id: int, content: str) -> list[db.AudioTrack]:
        with DbSession() as session:
            stmt = update(db.Section).returning(db.Section).where(db.Section.id == section_id).values(content=content)
            updated_section = session.execute(stmt).scalars().first()
            LOG.info("Updated section: \n%s", updated_section)
            session.commit()
            return self.audiotracks_service.generate_speech([updated_section]) if updated_section else []


SectionServiceDep = Annotated[SectionService, SectionService.dep()]
