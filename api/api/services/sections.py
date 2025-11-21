import threading
import time
import uuid
from queue import Queue

from fastapi.params import Depends
from sqlalchemy import delete, update

from api import get_logger
from api.models import db
from api.models.db import Section, DbSession
from api.services.files import FilesService

LOG = get_logger(__name__)


class SectionService:
    def __init__(self, files_service: FilesService = Depends()):
        self.files_service = files_service

    def delete_sections(self, book_id: uuid.UUID):
        with DbSession() as session:
            stmt = delete(Section).where(Section.book_id == book_id)
            session.execute(stmt)
            session.commit()

    def generate_speech(self, sections: list[Section]):
        LOG.info("Enqueueing speech generation for %s sections: \n%s", len(sections), sections)

        self.update_status(sections, db.SpeechStatus.queued)

        for section in sections:
            SpeechGenerationQueue.singleton.put(self, section)

    def update_status(self, sections: list[Section], status: db.SpeechStatus):
        with DbSession() as session:
            for section in sections:
                session.execute(update(db.Section).where(db.Section.id == section.id).values(speech_status=status))
            session.commit()


class SpeechGenerationQueue:
    singleton = None
    def __init__(self):
        self.queue = Queue()
        self.thread = threading.Thread(target=self._thread_target, daemon=True)
        self.thread.start()

    def put(self, section_service: SectionService, section: Section):
        self.queue.put((section_service, section))

    def _thread_target(self):
        LOG.info("Starting speech generation thread...")
        while True:
            service, section = self.queue.get()
            try:
                self._generate_speech(service, section)
            except Exception:
                LOG.exception("Error generating speech for section: \n%s", section)
                service.update_status([section], db.SpeechStatus.failed)
            finally:
                self.queue.task_done()

    def _generate_speech(self, section_service: SectionService, section: db.Section):
        LOG.info("Generating speech for section: \n%s", section)
        # Update status to generating.
        section_service.update_status([section], db.SpeechStatus.generating)
        time.sleep(15)

        # Generate phonemes.

        # Generate speech.

        # Store to object store.

        # Update status to ready.
        section_service.update_status([section], db.SpeechStatus.ready)
