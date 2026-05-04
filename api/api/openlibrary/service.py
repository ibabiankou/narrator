import logging
from typing import Annotated, Optional

from sqlalchemy import text

from api.models.domain import BookMetadata, MetadataCandidate
from api.openlibrary.model import Author, Edition
from common_lib.db import transactional
from common_lib.service import Service

LOG = logging.getLogger(__name__)


# noinspection PyTypeChecker
class OpenlibraryService(Service):
    def __init__(self, **kwargs):
        pass

    @transactional
    def edition_by_isbn(self, isbn: str) -> Optional[Edition]:
        query = text("""
                     select e.data
                     from edition_isbns ei
                              join editions e on e.key = ei.edition_key
                     where ei.isbn = :isbn
                     """)
        result = self.db.execute(query, {"isbn": isbn}).fetchone()
        if result is None:
            return None
        return Edition.model_validate(result[0])

    @transactional
    def edition_by_title_author(self, title: str, author: str) -> Optional[Edition]:
        query = text("""
                     select e.data
                     from editions e
                              join works w
                                   on w.key = e.work_key
                              join author_works a_w
                                   on a_w.work_key = w.key
                              join authors a
                                   on a_w.author_key = a.key
                     where e.data ->> 'title' = :title
                       and a.data ->> 'name' = :author;
                     """)
        result = self.db.execute(query, {"title": title, "author": author}).fetchone()
        if result is None:
            return None
        return Edition.model_validate(result[0])

    @transactional
    def autor_by_key(self, key: str) -> Optional[Author]:
        query = text("""
                     select a.data
                     from authors a
                     where a.key = :key;
                     """)
        result = self.db.execute(query, {"key": key}).fetchone()
        if result is None:
            return None
        return Author.model_validate(result[0])

    def cover_url(self, id: int) -> str:
        return f"https://covers.openlibrary.org/b/id/{id}.jpg"

    def search_matches(self, llm_candidate: BookMetadata) -> list[MetadataCandidate]:
        result = []
        edition_keys = set()

        for isbn in llm_candidate.isbns:
            edition = self.edition_by_isbn(isbn)
            if edition and edition.key not in edition_keys:
                result.append(self.edition_to_metadata_candidate(edition))
                edition_keys.add(edition.key)
        # TODO: consider ISBN matches as precise enough and merge those with LLM result.

        if llm_candidate.title is not None and llm_candidate.authors is not None:
            for author in llm_candidate.authors:
                edition = self.edition_by_title_author(llm_candidate.title, author)
                if edition and edition.key not in edition_keys:
                    result.append(self.edition_to_metadata_candidate(edition))
                    edition_keys.add(edition.key)

        return result

    def edition_to_metadata_candidate(self, edition: Edition) -> MetadataCandidate:
        cover_url = None
        if edition.covers and len(edition.covers) > 0:
            cover_url = self.cover_url(edition.covers[0])

        authors = []
        if edition.authors:
            for ref in edition.authors:
                author = self.autor_by_key(ref.key)
                if author:
                    authors.append(author.name)

        return MetadataCandidate(source="openlibrary",
                                 cover=cover_url,
                                 title=edition.title,
                                 series=", ".join(edition.series or []),
                                 description=edition.description.value if edition.description else None,
                                 authors=authors,
                                 isbns=edition.isbn_10 or [] + edition.isbn_13 or [])


OpenlibraryServiceDep = Annotated[OpenlibraryService, OpenlibraryService.dep()]
