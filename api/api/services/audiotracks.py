import threading
from queue import Queue

from fastapi.params import Depends
from sqlalchemy import update, insert, delete

from api import get_logger
from api.models import db
from api.models.db import DbSession
from api.services.files import FilesService
from api.services.kokoro import KokoroClient
from api.services.sections import SectionService

LOG = get_logger(__name__)


class AudioTrackService:
    def __init__(self,
                 section_service: SectionService = Depends(),
                 files_service: FilesService = Depends(),
                 kokoro_client: KokoroClient = Depends()):
        self.section_service = section_service
        self.files_service = files_service
        self.kokoro_client = kokoro_client

    def generate_speech(self, sections: list[db.Section]):
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
                        "status": db.AudioStatus.queued
                    }
                    for section in sections
                ]
            ).all()
            session.commit()
            for track in inserted_tracks:
                track_map[track.section_id] = track

        for section in sections:
            SpeechGenerationQueue.singleton.put(self, section, track_map[section.id])

    def delete_for_sections(self, sections: list[db.Section]):
        with DbSession() as session:
            ids = [section.id for section in sections]
            stmt = delete(db.AudioTrack).where(db.AudioTrack.section_id.in_(ids)).returning(db.AudioTrack)
            deleted_tracks = session.scalars(stmt).all()
            LOG.info("Deleted %s tracks: \n%s", len(deleted_tracks), deleted_tracks)
            session.commit()

    def save_track(self, track: db.AudioTrack):
        with DbSession() as session:
            session.execute(update(db.AudioTrack).where(db.AudioTrack.id == track.id).values(track.as_dict()))
            session.commit()

    def store_speech_file(self, section: db.Section, speech_data: bytes) -> str:
        file_name = f"{section.id}.mp3"
        self.files_service.store_speech_file(section.book_id, file_name, speech_data)
        return file_name


class SpeechGenerationQueue:
    singleton = None

    def __init__(self):
        self.queue = Queue()
        self.thread = threading.Thread(target=self._thread_target, daemon=True)
        self.thread.start()

    def put(self, audiotrack_service: AudioTrackService, section: db.Section, track: db.AudioTrack):
        self.queue.put((audiotrack_service, section, track))

    def _thread_target(self):
        LOG.info("Starting speech generation thread...")
        while True:
            service, section, track = self.queue.get()
            try:
                self._generate_speech(service, section, track)
            except Exception:
                LOG.exception("Error generating speech for section: \n%s", section)
                track.status = db.AudioStatus.failed
                service.save_track(track)
            finally:
                self.queue.task_done()

    def _generate_speech(self, audiotrack_service: AudioTrackService, section: db.Section, track: db.AudioTrack):
        LOG.info("Generating speech for section: \n%s", section)

        track.status = db.AudioStatus.generating
        audiotrack_service.save_track(track)

        phonemes = audiotrack_service.kokoro_client.phonemize(section.content)
        audiotrack_service.section_service.set_phonemes(section.id, phonemes)

        audio = audiotrack_service.kokoro_client.generate_from_phonemes(phonemes)
        file_name = audiotrack_service.store_speech_file(section, audio.content)

        track.status = db.AudioStatus.ready
        track.file_name = file_name
        track.duration = audio.duration

        audiotrack_service.save_track(track)
