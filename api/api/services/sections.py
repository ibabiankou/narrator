import logging
import uuid
from typing import Annotated

from sqlalchemy import delete, update, select, text
from sqlalchemy.exc import NoResultFound

from api.models import db, api
from api.services.audiotracks import AudioTrackServiceDep
from api.services.progress import PlaybackProgressServiceDep
from api.services.settings import SettingsServiceDep
from common_lib import RMQClientDep
from common_lib.db import transactional
from common_lib.models import rmq
from common_lib.service import Service

LOG = logging.getLogger(__name__)


# noinspection PyTypeChecker,SqlDialectInspection
class SectionService(Service):
    def __init__(self,
                 audiotracks_service: AudioTrackServiceDep,
                 progress_service: PlaybackProgressServiceDep,
                 rmq_client: RMQClientDep,
                 settings_service: SettingsServiceDep,
                 **kwargs):
        self.audiotracks_service = audiotracks_service
        self.progress_service = progress_service
        self.rmq_client = rmq_client
        self.settings_service = settings_service

    @transactional
    def get_sections(self, book_id: uuid.UUID) -> list[api.BookSection]:
        stmt = select(db.Section).where(db.Section.book_id == book_id).order_by(db.Section.section_index)
        db_sections = self.db.execute(stmt).scalars().all()

        api_sections = []
        for section in db_sections:
            book_section = api.BookSection(id=section.id,
                                           book_id=section.book_id,
                                           page_index=section.page_index,
                                           section_index=section.section_index,
                                           content=section.content)
            api_sections.append(book_section)
        return api_sections

    def get_section(self, section_id: int):
        return self.db.get(db.Section, section_id)

    @transactional
    def delete_sections(self, book_id: uuid.UUID = None, section_ids: list[int] = None):
        if not book_id and not section_ids:
            raise ValueError("Either book_id or section_ids must be provided")

        # Load the sections to be deleted.
        stmt = select(db.Section)
        if book_id:
            stmt = stmt.where(db.Section.book_id == book_id)
        if section_ids:
            stmt = stmt.where(db.Section.id.in_(section_ids))
        sections = self.db.scalars(stmt).all()

        if not sections:
            return []

        # Delete audio tracks corresponding to the sections being deleted.
        self.audiotracks_service.delete_for_sections(sections)

        # Delete the sections.

        stmt = delete(db.Section).returning(db.Section)
        if book_id:
            stmt = stmt.where(db.Section.book_id == book_id)
        if section_ids:
            stmt = stmt.where(db.Section.id.in_(section_ids))
        deleted_sections = self.db.execute(stmt).scalars().all()
        LOG.info("Deleted %s sections: \n%s", len(deleted_sections), deleted_sections)

        return deleted_sections

    def _set_phonemes(self, section_id: int, phonemes: str):
        self.db.execute(update(db.Section).where(db.Section.id == section_id).values(phonemes=phonemes))

    @transactional
    def handle_phonemes_msg(self, payload: rmq.PhonemesResponse):
        LOG.debug("Got phonemes for track %s, requesting speech synthesis...", payload.track_id)

        section = self.db.get(db.Section, payload.section_id)
        if section:
            self._set_phonemes(payload.section_id, payload.phonemes)
            self.audiotracks_service.synthesize_speech(payload.book_id, payload.section_id, payload.track_id,
                                                       payload.phonemes, voice=payload.voice)
        else:
            LOG.warning("Section %s seem to be missing, so ignoring the message...", payload.section_id)

    @transactional
    def set_content(self, section_id: int, content: str) -> list[api.AudioTrack]:
        stmt = update(db.Section).returning(db.Section).where(db.Section.id == section_id).values(content=content)
        updated_section = self.db.execute(stmt).scalars().first()
        LOG.info("Updated section: \n%s", updated_section)

        if updated_section is None:
            # Nothing was updated, so return empty list.
            raise NoResultFound()

        track_maybe = self.audiotracks_service.get_track_by_section_id(section_id)
        if track_maybe is None:
            # Updated section has corresponding track, so trigger speech generation for updated content.
            return []

        return self.audiotracks_service.generate_speech([updated_section])

    @transactional
    def is_owner(self, user_id: uuid.UUID, section_id: int) -> bool:
        query = "select owner_id = :owner_id from books where id = (select book_id from sections where id = :section_id)"
        return self.db.execute(text(query), {"owner_id": user_id, "section_id": section_id}).scalar()


SectionServiceDep = Annotated[SectionService, SectionService.dep()]
