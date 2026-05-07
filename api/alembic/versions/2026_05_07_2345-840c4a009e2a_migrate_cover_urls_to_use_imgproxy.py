"""Migrate cover_urls to use imgproxy

Revision ID: 840c4a009e2a
Revises: 2d8dad9aae9e
Create Date: 2026-05-07 23:45:31.965090

"""
import logging
from typing import Sequence, Union

from alembic import op
from sqlalchemy import update
from sqlalchemy.orm import Session

from api.models import db, domain
from api.utils.imgproxy import ImgProxy

# revision identifiers, used by Alembic.
revision: str = '840c4a009e2a'
down_revision: Union[str, Sequence[str], None] = '2d8dad9aae9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

img_proxy = ImgProxy()


def upgrade() -> None:
    """Upgrade data."""
    bind = op.get_bind()
    session = Session(bind=bind)

    # Load all books.
    all_books = session.query(db.Book).all()
    for book in all_books:
        metadata_candidates_maybe = book.metadata_candidates
        if metadata_candidates_maybe is None:
            continue

        should_update = False
        candidates: list[domain.MetadataCandidate] = metadata_candidates_maybe.candidates

        # use first candidate cover image to generate imgproxy url for book.
        if len(candidates) > 0 and candidates[0].cover:
            raw_image_url = f"/{candidates[0].cover}"
            proxy_url = img_proxy.build_url(raw_image_url)
            book.cover = proxy_url
            should_update = True

        for candidate in candidates:
            if candidate.cover:
                raw_image_url = f"/{candidate.cover}"
                proxy_url = img_proxy.build_url(raw_image_url)
                candidate.cover = proxy_url
                should_update = True

        if should_update:
            stmt = update(db.Book).where(db.Book.id == book.id).values(cover=book.cover,
                                                                       metadata_candidates=metadata_candidates_maybe)
            session.execute(stmt)

    session.commit()


def downgrade() -> None:
    """Downgrade data."""
    # If cover image of book or candidates is imgproxy image, extract source image and use it.
    pass
