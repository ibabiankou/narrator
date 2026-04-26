import logging
import uuid
from typing import Annotated, Optional

from sqlalchemy import update, select, delete

from api.models import db
from api.models.db import DbSession
from common_lib.service import Service

LOG = logging.getLogger(__name__)


class PlaybackProgressService(Service):

    def get_playback_info(self, user_id: uuid.UUID, book_id: uuid.UUID) -> Optional[db.PlaybackProgress]:
        with DbSession() as session:
            return session.scalar(select(db.PlaybackProgress).where(db.PlaybackProgress.user_id == user_id).where(db.PlaybackProgress.book_id == book_id))

    def upsert_progress(self, progress: db.PlaybackProgress):
        with DbSession() as session:
            stmt = select(db.PlaybackProgress).where(db.PlaybackProgress.user_id == progress.user_id).where(db.PlaybackProgress.book_id == progress.book_id)
            existing = session.scalar(stmt)

            if existing:
                stmt = update(db.PlaybackProgress).returning(db.PlaybackProgress).where(
                    db.PlaybackProgress.user_id == progress.user_id).where(
                    db.PlaybackProgress.book_id == progress.book_id).values(progress.as_dict())
                session.execute(stmt)
            else:
                session.add(progress)

            session.commit()

    def delete(self, user_id: uuid.UUID, book_id: uuid.UUID):
        with DbSession() as session:
            stmt = delete(db.PlaybackProgress).where(db.PlaybackProgress.user_id == user_id).where(db.PlaybackProgress.book_id == book_id).returning(db.PlaybackProgress)
            deleted_items = session.scalars(stmt).all()
            LOG.info("Deleted %s records: \n%s", len(deleted_items), deleted_items)
            session.commit()


PlaybackProgressServiceDep = Annotated[PlaybackProgressService, PlaybackProgressService.dep()]
