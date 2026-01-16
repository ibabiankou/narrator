import uuid
from dataclasses import dataclass
from typing import Annotated, Optional

from sqlalchemy import text, update, select, delete

from api import get_logger
from api.models import db
from api.models.db import DbSession, BookStatus
from common_lib.service import Service

LOG = get_logger(__name__)


@dataclass
class ProgressData:
    playback_progress: Optional[db.PlaybackProgress]
    stats: dict


class PlaybackProgressService(Service):

    def get_progress(self, book_id: uuid.UUID) -> Optional[ProgressData]:
        query = """
                select coalesce(sum(length(s.content)), 0) as length, 'total' as type
                from sections s
                where s.book_id = :book_id
                union
                select coalesce(sum(a.duration), 0) as length, 'played_duration' as type
                from audio_tracks a
                where a.book_id = :book_id
                  and a.section_id < (select section_id from playback_progress where book_id = :book_id)
                union
                select coalesce(sum(a.duration), 0) as length, 'narrated_duration' as type
                from audio_tracks a
                where a.book_id = :book_id
                union
                select coalesce(sum(length(s.content)), 0) as length, 'available' as type
                from sections s
                         join audio_tracks a on s.id = a.section_id
                where s.book_id = :book_id
                  and a.status = 'ready'
                union
                select coalesce(sum(length(s.content)), 0) as length, 'queued' as type
                from sections s
                         join audio_tracks a on s.id = a.section_id
                where s.book_id = :book_id
                  and a.status = 'queued'
                union
                select coalesce(sum(length(s.content)), 0) as length, 'missing' as type
                from sections s
                         left join audio_tracks a on s.id = a.section_id
                where s.book_id = :book_id
                  and a.id is null \
                """

        narration_stats = {}
        with DbSession() as session:
            book = session.get_one(db.Book, book_id)
            if book.status != BookStatus.ready:
                return None
            rs = session.execute(text(query), {"book_id": book_id})
            for length, stat_type in rs:
                narration_stats[stat_type] = length
            progress = session.scalar(select(db.PlaybackProgress).where(db.PlaybackProgress.book_id == book_id))

        return ProgressData(progress, narration_stats)

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


PlaybackProgressServiceDep = Annotated[PlaybackProgressService, PlaybackProgressService.dep()]
