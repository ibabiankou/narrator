import logging
import uuid
from typing import Annotated, Optional

from sqlalchemy import update, select, delete

from api.models import db, api
from common_lib.db import transactional
from common_lib.service import Service

LOG = logging.getLogger(__name__)


# noinspection PyTypeChecker
class PlaybackProgressService(Service):

    def __init__(self, **kwargs):
        pass

    @transactional
    def get_playback_info(self, user_id: uuid.UUID, book_id: uuid.UUID) -> api.PlaybackInfo:
        stmt = (select(db.PlaybackProgress)
                .where(db.PlaybackProgress.user_id == user_id)
                .where(db.PlaybackProgress.book_id == book_id)
                )
        playback_info = self.db.scalar(stmt)
        return api.PlaybackInfo(book_id=book_id, data=playback_info.data if playback_info else {})

    @transactional
    def upsert_progress(self, progress: db.PlaybackProgress):
        stmt = select(db.PlaybackProgress).where(db.PlaybackProgress.user_id == progress.user_id).where(
            db.PlaybackProgress.book_id == progress.book_id)
        existing = self.db.scalar(stmt)

        if existing:
            stmt = update(db.PlaybackProgress).returning(db.PlaybackProgress).where(
                db.PlaybackProgress.user_id == progress.user_id).where(
                db.PlaybackProgress.book_id == progress.book_id).values(progress.as_dict())
            self.db.execute(stmt)
        else:
            self.db.add(progress)

    def delete(self, user_id: uuid.UUID, book_id: uuid.UUID):
        stmt = delete(db.PlaybackProgress).where(db.PlaybackProgress.user_id == user_id).where(
            db.PlaybackProgress.book_id == book_id).returning(db.PlaybackProgress)
        deleted_items = self.db.scalars(stmt).all()
        LOG.info("Deleted %s records: \n%s", len(deleted_items), deleted_items)


PlaybackProgressServiceDep = Annotated[PlaybackProgressService, PlaybackProgressService.dep()]
