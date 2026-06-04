import asyncio
import logging
from datetime import datetime, UTC
from typing import Sequence, List

from sqlalchemy import select, text, update

from api.models import db
from api.services.settings import SettingsServiceDep
from common_lib import RMQClientDep
from common_lib.db import transactional
from common_lib.models import rmq
from common_lib.rmq import Topology
from common_lib.service import Service

LOG = logging.getLogger(__name__)


class NarrationQueueService(Service):
    def __init__(self,
                 rmq_client: RMQClientDep,
                 settings_service: SettingsServiceDep,
                 **kwargs):
        self.rmq_client = rmq_client
        self.settings_service = settings_service

    async def generate_speech_maybe(self):
        while True:
            LOG.info("Checking if need to generate some speech...")
            try:
                self._do_generate_speech_maybe()
            except:
                LOG.info("Error while triggering speech generation, will try again later.", exc_info=True)

            settings = self.settings_service.get_system_settings()
            await asyncio.sleep(settings.speech_generation_interval_sec)

    @transactional
    def _do_generate_speech_maybe(self):
        system_settings = self.settings_service.get_system_settings()
        if not system_settings.speech_generation_enabled:
            LOG.info("Speech generation is disabled. Doing nothing.")
            return

        message_num = 0
        message_num += self.rmq_client.get_queue_size(Topology.narration_queue)

        if message_num > system_settings.speech_generation_queue_size_threshold:
            return

        # Get next 10 tracks to generate and publish them to RMQ.
        # noinspection SqlDialectInspection
        query_text = """WITH BooksToNarrate as (select b.id, b.created_time
                                                from books b
                                                where b.status = 'narrating'
                                                order by b.created_time
                                                limit 1)
                        SELECT *
                        FROM narration_queue q
                        WHERE q.book_id in (SELECT id FROM BooksToNarrate)
                          and q.sent is null
                        ORDER BY q."order"
                        LIMIT 10 FOR UPDATE
                     """

        stmt = select(db.NarrationQueue).from_statement(text(query_text))
        # noinspection PyTypeChecker
        db_records: Sequence[db.NarrationQueue] = self.db.scalars(stmt).all()
        if len(db_records):
            stmt = update(db.NarrationQueue).where(db.NarrationQueue.id.in_([r.id for r in db_records])).values(
                sent=datetime.now(UTC))
            # noinspection PyTypeChecker
            self.db.execute(stmt)

            self._send_rmq_messages(list(db_records))

    def _send_rmq_messages(self, queue_entries: List[db.NarrationQueue]):
        for entry in queue_entries:
            msg = rmq.NarrateRequest(
                queue_id=entry.id,
                book_id=entry.book_id,
                tts_model=entry.tts_model,
                voice=entry.voice,
                track_base_name=entry.track_base_name,
                order=entry.order,
                fragments=entry.fragments
            )
            self.rmq_client.publish("narrate", msg)
