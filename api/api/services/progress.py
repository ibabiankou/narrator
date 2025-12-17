import uuid

from sqlalchemy import text, update, select

from api import get_logger
from api.models import db
from api.models.db import DbSession


LOG = get_logger(__name__)

class PlaybackProgressService:

    def get_progress(self, book_id: uuid.UUID) -> tuple[db.PlaybackProgress, dict[str, int]]:
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
            # TODO: For some reason the result of the query is cached between requests. Find a way to disable the cache
            #  in this particular case.
            rs = session.execute(text(query), {"book_id": book_id})
            for length, stat_type in rs:
                narration_stats[stat_type] = length
            progress = session.scalar(select(db.PlaybackProgress).where(db.PlaybackProgress.book_id == book_id))

        return progress, narration_stats

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
