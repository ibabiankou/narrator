import uuid
from typing import List, Annotated, Optional

from sqlalchemy import update, insert, delete, select

from api import get_logger
from api.models import db, api
from api.models.db import DbSession
from api.services.files import FilesServiceDep
from common_lib import RMQClientDep
from common_lib.models import rmq
from common_lib.service import Service

LOG = get_logger(__name__)


class AudioTrackService(Service):
    def __init__(self,
                 files_service: FilesServiceDep,
                 rmq_client: RMQClientDep):
        self.files_service = files_service
        self.rmq_client = rmq_client

    def generate_speech(self, sections: list[db.Section]) -> List[api.AudioTrack]:
        LOG.info("Enqueueing speech generation for %s sections: \n%s", len(sections), sections)
        self.delete_for_sections(sections)

        track_map = {}
        with DbSession() as session:
            inserted_tracks = session.scalars(
                insert(db.AudioTrack).returning(db.AudioTrack),
                [
                    {
                        "book_id": section.book_id,
                        "section_id": section.id,
                        "playlist_order": section.section_index,
                        "status": db.AudioStatus.queued
                    }
                    for section in sections
                ]
            ).all()
            for track in inserted_tracks:
                track_map[track.section_id] = track
            for section in sections:
                track_id = track_map[section.id].id
                self.phonemize_text(section.book_id, section.id, track_id, section.content)

            session.commit()

            return [
                api.AudioTrack(book_id=track.book_id,
                               section_id=track.section_id,
                               status=track.status,
                               file_name=track.file_name,
                               duration=track.duration)
                for track in inserted_tracks
            ]
    def phonemize_text(self, book_id: uuid.UUID, section_id: int, track_id: int, content: str):
        msg = rmq.PhonemizeText(book_id=book_id, section_id=section_id, track_id=track_id, text=content)
        self.rmq_client.publish("phonemize", msg)

    def _get_track(self, track_id: int) -> Optional[db.AudioTrack]:
        with DbSession() as session:
            stmt = select(db.AudioTrack).where(db.AudioTrack.id == track_id)
            return session.scalars(stmt).first()

    def synthesize_speech(self, book_id: uuid.UUID, section_id: int, track_id: int, phonemes: str):
        file_path = self.files_service.speech_filename(book_id, f"{track_id}.mp3")
        msg = rmq.SynthesizeSpeech(book_id=book_id, section_id=section_id, track_id=track_id, phonemes=phonemes,
                                   file_path=file_path)
        self.rmq_client.publish("synthesize", msg)

    def delete_for_sections(self, sections: list[db.Section]):
        with DbSession() as session:
            ids = [section.id for section in sections]
            stmt = delete(db.AudioTrack).where(db.AudioTrack.section_id.in_(ids)).returning(db.AudioTrack)
            deleted_tracks = session.scalars(stmt).all()
            LOG.info("Deleted %s tracks: \n%s", len(deleted_tracks), deleted_tracks)
            for track in deleted_tracks:
                self.files_service.delete_speech_file(track.book_id, track.file_name)
            session.commit()

    def handle_speech_msg(self, payload: rmq.SpeechResponse):
        LOG.debug("Speech is ready for track %s.", payload.track_id)
        track = self._get_track(payload.track_id)
        track.status = db.AudioStatus.ready
        track.file_name = payload.file_path.split("/")[-1]
        track.duration = payload.duration
        self.save_track(track)

    def save_track(self, track: db.AudioTrack):
        with DbSession() as session:
            session.execute(update(db.AudioTrack).where(db.AudioTrack.id == track.id).values(track.as_dict()))
            session.commit()

    def get_tracks(self, book_id: uuid.UUID, sections: List[int] = None) -> List[db.AudioTrack]:
        with DbSession() as session:
            stmt = select(db.AudioTrack).where(db.AudioTrack.book_id == book_id)
            if sections:
                stmt = stmt.where(db.AudioTrack.section_id.in_(sections))
            stmt = stmt.order_by(db.AudioTrack.playlist_order)
            return list(session.execute(stmt).scalars().all())

AudioTrackServiceDep = Annotated[AudioTrackService, AudioTrackService.dep()]
