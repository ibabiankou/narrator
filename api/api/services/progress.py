import uuid

from sqlalchemy import text, update, select
from sqlalchemy.dialects.postgresql import insert

from api.models import db
from api.models.db import DbSession, NotFound


class PlaybackProgressService:

    def get_progress(self, book_id: uuid.UUID) -> (db.PlaybackProgress, dict[str, int]):
        query = """
                select sum(length(s.content)) as length, 'total' as type
                from sections s 
                where s.book_id = :book_id
                union
                select coalesce(sum(length(s.content)), 0) as length, 'available' as type
                from sections s join audio_tracks a on s.id = a.section_id
                where s.book_id = :book_id and a.status = 'ready'
                union
                select coalesce(sum(length(s.content)), 0) as length, 'queued' as type
                from sections s join audio_tracks a on s.id = a.section_id
                where s.book_id = :book_id and a.status = 'queued'
                union
                select coalesce(sum(length(s.content)), 0) as length,  'missing' as type
                from sections s left join audio_tracks a on s.id = a.section_id
                where s.book_id = :book_id and a.id is null
        """

        narration_stats = {}
        with DbSession() as session:
            rs = session.execute(text(query), {"book_id": book_id})
            for length, type in rs:
                narration_stats[type] = length

        return None, narration_stats

    def upsert_progress(self, progress: db.PlaybackProgress):
        with DbSession() as session:
            stmt = select(db.PlaybackProgress).where(db.PlaybackProgress.book_id == progress.book_id)
            existing = session.scalar(stmt)

            if existing:
                stmt = update(db.PlaybackProgress).returning(db.PlaybackProgress).where(
                    db.PlaybackProgress.id == progress.id).values(progress.as_dict())
                session.execute(stmt)
            else:
                session.add(progress)

            session.commit()
