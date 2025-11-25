import uuid

from fastapi.params import Depends
from sqlalchemy import delete, update

from api import get_logger
from api.models import db
from api.models.db import Section, DbSession
from api.services.files import FilesService
from api.services.kokoro import KokoroClient

LOG = get_logger(__name__)


class SectionService:
    def __init__(self, files_service: FilesService = Depends(), kokoro_client: KokoroClient = Depends()):
        self.files_service = files_service
        self.kokoro_client = kokoro_client

    def delete_sections(self, book_id: uuid.UUID):
        with DbSession() as session:
            stmt = delete(Section).where(Section.book_id == book_id)
            session.execute(stmt)
            session.commit()

    def set_phonemes(self, section_id: int, phonemes: str):
        with DbSession() as session:
            session.execute(update(db.Section).where(db.Section.id == section_id).values(phonemes=phonemes))
            session.commit()
