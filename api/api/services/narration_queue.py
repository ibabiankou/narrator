from io import BytesIO

import asyncio
import logging
import m3u8
from datetime import datetime, UTC
from typing import Sequence, List

from sqlalchemy import select, text, update

from api.models import db
from api.services.files import FilesServiceDep
from api.services.settings import SettingsServiceDep
from common_lib import RMQClientDep
from common_lib.db import transactional
from common_lib.models import rmq, tts
from common_lib.models.tts import TrackManifest
from common_lib.rmq import Topology
from common_lib.service import Service

LOG = logging.getLogger(__name__)


class NarrationQueueService(Service):
    def __init__(self,
                 rmq_client: RMQClientDep,
                 settings_service: SettingsServiceDep,
                 files_service: FilesServiceDep,
                 **kwargs):
        self.rmq_client = rmq_client
        self.settings_service = settings_service
        self.files_service = files_service

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

    @transactional
    def handle_response_msg(self, payload: rmq.NarrateResponse):
        LOG.info("Got response for narration request %s. Will update the playlist.", payload.queue_id)
        db_record = self.db.get(db.NarrationQueue, payload.queue_id)
        db_record.completed = payload.completed
        db_record.narration_time_s = payload.narration_time_s
        db_record.duration_s = payload.duration_s
        db_record.size_bytes = payload.size_bytes

        # Load all track manifests to generate the playlist
        audio_dir = f"{db_record.book_id}/audio-files/{db_record.tts_model}/{db_record.voice}"
        all_files = self.files_service.list_files(audio_dir)
        track_manifest_files = [f for f in all_files if f.endswith(".json")]
        track_manifests = []
        for track_manifest_key in track_manifest_files:
            file_data = self.files_service.get_object(track_manifest_key)
            track_manifests.append(TrackManifest.model_validate_json(file_data.body))
        # Ensure tracks are ordered correctly.
        track_manifests.sort(key=lambda t: t.timeline[0].id)

        # Or simply order by the first fragment ID? < Do this one for now.
        # TODO: Might do complete cross-check upon book completion.

        playlist_key = f"{db_record.book_id}/playlists/{db_record.tts_model}_{db_record.voice}.m3u8"
        playlist = self._generate_playlist(track_manifests)
        self.files_service.upload_file(playlist_key, BytesIO(playlist.encode()))

    def _generate_playlist(self, tracks: List[tts.TrackManifest]) -> str:
        playlist = m3u8.M3U8()

        playlist.version = "4"
        playlist.target_duration = max([sum([f.duration for f in t.timeline]) for t in tracks] or [0]) + 1
        playlist.media_sequence = 0
        # TODO: Set endlist to True if the book status is ready (no narration happens).
        playlist.is_endlist = False

        for track in tracks:
            segment = m3u8.Segment(
                uri=f"/api/files/{track.audio_key}",
                duration=sum([f.duration for f in track.timeline]),
                discontinuity=True
            )
            playlist.segments.append(segment)

        return playlist.dumps()
