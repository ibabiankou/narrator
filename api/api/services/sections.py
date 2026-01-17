import asyncio
import os
import uuid
from typing import Annotated

from sqlalchemy import delete, update, select, text

from api import get_logger
from api.models import db, api
from api.models.db import DbSession
from api.services.audiotracks import AudioTrackServiceDep
from api.services.progress import PlaybackProgressServiceDep
from common_lib import RMQClientDep
from common_lib.models import rmq
from common_lib.rmq import Topology
from common_lib.service import Service

LOG = get_logger(__name__)


class SectionService(Service):
    def __init__(self,
                 audiotracks_service: AudioTrackServiceDep,
                 progress_service: PlaybackProgressServiceDep,
                 rmq_client: RMQClientDep):
        self.audiotracks_service = audiotracks_service
        self.progress_service = progress_service
        self.rmq_client = rmq_client

        self._speech_generation_interval_sec = os.getenv("SPEECH_GENERATION_INTERVAL_SEC", 30)
        self._speech_generation_queue_size_threshold = os.getenv("SPEECH_GENERATION_QUEUE_SIZE_THRESHOLD", 10)

    def get_sections(self, book_id: uuid.UUID):
        with DbSession() as session:
            stmt = select(db.Section).where(db.Section.book_id == book_id).order_by(db.Section.section_index)
            return session.execute(stmt).scalars().all()

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

    def handle_phonemes_msg(self, payload: rmq.PhonemesResponse):
        LOG.debug("Got phonemes for track %s, requesting speech synthesis...", payload.track_id)
        with DbSession() as session:
            section = session.get(db.Section, payload.section_id)
            if section:
                self.set_phonemes(payload.section_id, payload.phonemes)
                self.audiotracks_service.synthesize_speech(payload.book_id, payload.section_id, payload.track_id,
                                                           payload.phonemes, voice=payload.voice)
            else:
                LOG.warn("Section %s seem to be missing, so ignoring the message...", payload.section_id)

    def set_content(self, section_id: int, content: str) -> list[api.AudioTrack]:
        with DbSession() as session:
            stmt = update(db.Section).returning(db.Section).where(db.Section.id == section_id).values(content=content)
            updated_section = session.execute(stmt).scalars().first()
            LOG.info("Updated section: \n%s", updated_section)
            session.commit()
            return self.audiotracks_service.generate_speech([updated_section]) if updated_section else []

    async def generate_speech_maybe(self):
        while True:
            LOG.info("Checking if need to generate some speech...")
            self._do_generate_speech_maybe()
            await asyncio.sleep(self._speech_generation_interval_sec)

    def _do_generate_speech_maybe(self):
        message_num = self.rmq_client.get_queue_size(Topology.phonemization_queue)
        message_num += self.rmq_client.get_queue_size(Topology.speech_gen_queue)

        if message_num > self._speech_generation_queue_size_threshold:
            return

        # Find a few sections per book and trigger generation for them.
        # noinspection SqlDialectInspection
        query_text = """WITH MissingAudio AS (SELECT s.id,
                                                     s.book_id,
                                                     s.section_index,
                                                     -- Generate a rank for each section within its own book group
                                                     ROW_NUMBER() OVER (
                                                         PARTITION BY s.book_id
                                                         ORDER BY s.section_index ASC
                                                     ) as rank_in_book
                                              FROM sections s
                                                       LEFT JOIN audio_tracks a ON s.id = a.section_id
                                              WHERE a.id IS NULL)
                        SELECT *
                        FROM sections
                        WHERE id in (SELECT id 
                                     FROM MissingAudio 
                                     WHERE rank_in_book <= 5 
                                     ORDER BY book_id, section_index)"""
        with DbSession() as session:
            db_sections = session.scalars(select(db.Section).from_statement(text(query_text))).all()
            self.audiotracks_service.generate_speech(db_sections)


SectionServiceDep = Annotated[SectionService, SectionService.dep()]
