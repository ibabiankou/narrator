import asyncio
import logging
import os
import uuid
from typing import Annotated

from sqlalchemy import delete, update, select, text

from api.models import db, api
from api.services.audiotracks import AudioTrackServiceDep
from api.services.progress import PlaybackProgressServiceDep
from api.services.settings import SettingsServiceDep
from common_lib import RMQClientDep
from common_lib.db import transactional
from common_lib.models import rmq
from common_lib.rmq import Topology
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

        self._speech_generation_interval_sec = int(os.getenv("SPEECH_GENERATION_INTERVAL_SEC", 30))
        self._speech_generation_queue_size_threshold = int(os.getenv("SPEECH_GENERATION_QUEUE_SIZE_THRESHOLD", 10))

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
            return []

        track_maybe = self.audiotracks_service.get_track_by_section_id(section_id)
        if track_maybe is None:
            # Updated section has corresponding track, so trigger speech generation for updated content.
            return []

        return self.audiotracks_service.generate_speech([updated_section])

    async def generate_speech_maybe(self):
        while True:
            LOG.info("Checking if need to generate some speech...")
            try:
                self._do_generate_speech_maybe()
            except:
                LOG.info("Error while triggering speech generation, will try again later.", exc_info=True)
            await asyncio.sleep(self._speech_generation_interval_sec)

    @transactional
    def _do_generate_speech_maybe(self):
        system_settings = self.settings_service.get_system_settings()
        if not system_settings.speech_generation_enabled:
            LOG.info("Speech generation is disabled. Doing nothing.")
            return

        message_num = 0
        message_num += self.rmq_client.get_queue_size(Topology.phonemization_queue)
        message_num += self.rmq_client.get_queue_size(Topology.speech_gen_queue)

        if message_num > self._speech_generation_queue_size_threshold:
            return

        # Find a few sections per book and trigger generation for them.
        # noinspection SqlDialectInspection
        query_text = """WITH BooksToNarrate as (select distinct b.id, b.created_time
                                                from books b
                                                         join sections s on b.id = s.book_id
                                                         left join audio_tracks t on s.id = t.section_id
                                                where t.id is null and b.status = 'narrating'
                                                order by b.created_time
                                                limit 1), 
                            MissingAudio AS (SELECT s.id, s.book_id, s.section_index,
                                                -- Generate a rank for each section within its own book group
                                                ROW_NUMBER() OVER (
                                                    PARTITION BY s.book_id
                                                    ORDER BY s.section_index ASC
                                                ) as rank_in_book
                                             FROM sections s
                                                 LEFT JOIN audio_tracks a
                                             ON s.id = a.section_id
                                             WHERE s.book_id in (select id from BooksToNarrate)
                                               and a.id IS NULL)
        SELECT *
        FROM sections
        WHERE id in (SELECT id
                     FROM MissingAudio
                     WHERE rank_in_book <= 5
                     ORDER BY book_id, section_index)"""

        db_sections = self.db.scalars(select(db.Section).from_statement(text(query_text))).all()
        if len(db_sections):
            self.audiotracks_service.generate_speech(db_sections)

    @transactional
    def is_owner(self, user_id: uuid.UUID, section_id: int) -> bool:
        query = "select owner_id = :owner_id from books where id = (select book_id from sections where id = :section_id)"
        return self.db.execute(text(query), {"owner_id": user_id, "section_id": section_id}).scalar()


SectionServiceDep = Annotated[SectionService, SectionService.dep()]
