import logging
import uuid
from typing import Annotated, Optional

from pydantic import ValidationError
from sqlalchemy import text

from api.models.domain import BookMetadata, MetadataCandidate
from api.openlibrary.model import Author, Edition
from api.services.files import FilesServiceDep
from api.utils.isbn import validate_isbn, expand_isbns
from common_lib.db import transactional
from common_lib.service import Service

LOG = logging.getLogger(__name__)


# noinspection PyTypeChecker
class OpenlibraryService(Service):
    def __init__(self, files_service: FilesServiceDep, **kwargs):
        self.files_service = files_service

    @transactional
    def edition_by_isbn(self, isbn: str) -> Optional[Edition]:
        query = text("""
                     select e.data, e.key
                     from edition_isbns ei
                              join editions e on e.key = ei.edition_key
                     where ei.isbn = :isbn
                     """)
        result = self.db.execute(query, {"isbn": isbn}).fetchone()
        if result is None:
            return None
        try:
            return Edition.model_validate(result[0])
        except ValidationError as e:
            edition_key = result[1]
            LOG.error("Error loading edition %s by ISBN %s.", edition_key, isbn, exc_info=e)
            return None

    @transactional
    def edition_by_title_author(self, title: str, author: str) -> Optional[Edition]:
        query = text("""
                     select e.data, e.key
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
        try:
            return Edition.model_validate(result[0])
        except ValidationError as e:
            edition_key = result[1]
            LOG.error("Error loading edition %s by title '%s' and author '%s'.", edition_key, title, author, exc_info=e)
            return None

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
        try:
            return Author.model_validate(result[0])
        except ValidationError as e:
            LOG.error("Error loading author %s.", key, exc_info=e)
            return None

    def cover_url(self, id: int) -> str:
        return f"https://covers.openlibrary.org/b/id/{id}.jpg"

    def search_matches(self, book_id: uuid.UUID, llm_candidate: BookMetadata) -> list[MetadataCandidate]:
        result = []
        edition_keys = set()

        for isbn in expand_isbns(llm_candidate.isbns):
            edition = self.edition_by_isbn(isbn)
            if edition and edition.key not in edition_keys:
                result.append(self.edition_to_metadata_candidate(book_id, edition))
                edition_keys.add(edition.key)
        # TODO: consider ISBN matches as precise enough and merge those with LLM result.

        # TODO: fetch other editions by work_id from DB.

        if llm_candidate.title is not None and llm_candidate.authors is not None:
            for author in llm_candidate.authors:
                edition = self.edition_by_title_author(llm_candidate.title, author)
                if edition and edition.key not in edition_keys:
                    result.append(self.edition_to_metadata_candidate(book_id, edition))
                    edition_keys.add(edition.key)

        return result

    def edition_to_metadata_candidate(self, book_id: uuid.UUID, edition: Edition) -> MetadataCandidate:
        cover_url = None
        if edition.covers and len(edition.covers) > 0:
            # TODO: Consider if I need to use other covers.
            remote_cover_url = self.cover_url(edition.covers[0])
            covers_prefix = f"{book_id}/images/covers"
            cover_url = self.files_service.upload_remote_file(covers_prefix, remote_cover_url)

        authors = []
        if edition.authors:
            for ref in edition.authors:
                author = self.autor_by_key(ref.key)
                if author:
                    authors.append(author.name)

        valid_isbns = []
        for isbn in edition.isbn_10 or [] + edition.isbn_13 or []:
            if validate_isbn(isbn):
                valid_isbns.append(isbn)

        return MetadataCandidate(source="openlibrary",
                                 cover=cover_url,
                                 title=edition.title,
                                 series=", ".join(edition.series or []),
                                 description=edition.get_description(),
                                 authors=authors,
                                 isbns=valid_isbns)


OpenlibraryServiceDep = Annotated[OpenlibraryService, OpenlibraryService.dep()]
