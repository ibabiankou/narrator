import uuid
from dataclasses import dataclass
from typing import Annotated, Optional

from sqlalchemy import text, update, select, delete

from api import get_logger
from api.models import db
from api.models.db import DbSession, BookStatus
from common_lib.service import Service

LOG = get_logger(__name__)


class PlaybackProgressService(Service):

    def get_playback_info(self, book_id: uuid.UUID) -> Optional[db.PlaybackProgress]:
        with DbSession() as session:
            return session.scalar(select(db.PlaybackProgress).where(db.PlaybackProgress.book_id == book_id))

    def upsert_progress(self, progress: db.PlaybackProgress):
        with DbSession() as session:
            stmt = select(db.PlaybackProgress).where(db.PlaybackProgress.book_id == progress.book_id)
            existing = session.scalar(stmt)

            if existing:
                stmt = update(db.PlaybackProgress).returning(db.PlaybackProgress).where(
                    db.PlaybackProgress.book_id == progress.book_id).values(progress.as_dict())
                session.execute(stmt)
            else:
                session.add(progress)

            session.commit()

    def delete(self, book_id: uuid.UUID):
        with DbSession() as session:
            stmt = delete(db.PlaybackProgress).where(db.PlaybackProgress.book_id == book_id).returning(
                db.PlaybackProgress)
            deleted_items = session.scalars(stmt).all()
            LOG.info("Deleted %s records: \n%s", len(deleted_items), deleted_items)
            session.commit()


PlaybackProgressServiceDep = Annotated[PlaybackProgressService, PlaybackProgressService.dep()]
