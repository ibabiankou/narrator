import logging
from io import BytesIO
from typing import Annotated, Optional, Tuple, List, Dict

from blake3 import blake3
from sqlalchemy import select, text

from api.procurement.domain import IdMatch, ImageMatch
from api.procurement.models import EpubFile, MetadataId, ImagePhash
from common_lib.db import transactional
from common_lib.service import Service
from epub_lib import Epub
from epub_lib.util.id import normalize_identifier

LOG = logging.getLogger(__name__)


class ProcurementService(Service):
    def __init__(self, **kwargs):
        pass

    @transactional
    def upload(self, filename: str, body: BytesIO):
        hasher = blake3()
        hasher.update(body.getbuffer())
        file_hash = hasher.hexdigest()

        epub_file_maybe = self._find_file_by_hash(file_hash)
        if epub_file_maybe is not None:
            LOG.info("Found exact match of the uploaded file, stopping processing.")
            return

        # Extract metadata
        epub = Epub(body, filename=filename)
        metadata: dict = epub.package.metadata.model_dump(exclude_none=True)

        id_matches, ids_to_store = self._match_identifiers(epub)

        image_matches: List[ImageMatch] = []
        image_phash_maybe = self._calculate_cover_phash(epub)
        if image_phash_maybe is not None:
            image_matches = self._match_images(image_phash_maybe.image_name, image_phash_maybe.phash)

        epub_file = EpubFile(file_name=filename,
                             file_hash=file_hash,
                             file_size_bytes=len(body.getbuffer()),
                             raw_metadata=metadata,
                             id_matches=id_matches,
                             cover_matches=image_matches
                             )
        self.db.add(epub_file)
        self.db.flush()

        # Store EPUB Identifiers.
        for i in ids_to_store.values():
            i.source_file = epub_file.id
        self.db.add_all(ids_to_store.values())

        # Store cover image pHash
        if image_phash_maybe is not None:
            image_phash_maybe.source_file = epub_file.id
            self.db.add(image_phash_maybe)

    def _match_identifiers(self, epub) -> Tuple[List[IdMatch], Dict[str, MetadataId]]:
        ids_to_store = {}
        id_matches = []
        for id in epub.package.metadata.identifier:
            if id.value is None:
                LOG.debug("Skipping identifier without value.")
                continue

            id_type, id_value = normalize_identifier(id.value)
            if id_type == "calibre":
                LOG.debug("Skipping calibre ID, assuming they are not global. Book: '%s', ID: '%s'",
                          epub.filename, id_value)
                continue
            if id_value in ids_to_store:
                LOG.debug("Skipping already processed ID: %s.", id_value)
                continue

            metadata_id_maybe = self._find_metadata_id(id_type, id_value)
            if metadata_id_maybe is not None:
                # If matched with a known ID, store the match information and continue.
                id_matches.append(IdMatch(type=id_type, value=id_value, other_book_id=metadata_id_maybe.source_file))
            else:
                # Only store normalized ID if it was not matched to an existing ID.
                ids_to_store[id_value] = MetadataId(type=id_type, value=id_value)
        return id_matches, ids_to_store

    def _find_file_by_hash(self, file_hash: str) -> Optional[EpubFile]:
        stmt = select(EpubFile).where(EpubFile.file_hash == file_hash)
        # noinspection PyTypeChecker
        return self.db.scalars(stmt).first()

    def _find_metadata_id(self, id_type: str, id_value: str) -> Optional[MetadataId]:
        stmt = select(MetadataId).where(MetadataId.type == id_type).where(MetadataId.value == id_value)
        # noinspection PyTypeChecker
        return self.db.scalars(stmt).first()

    def _calculate_cover_phash(self, epub) -> Optional[ImagePhash]:
        cover_phash_maybe = epub.get_cover_phash()
        if cover_phash_maybe is None:
            return None
        image_name, image_phash = cover_phash_maybe
        binary_phash_str = bin(int(image_phash, 16))[2:].zfill(64)
        return ImagePhash(image_name=image_name, phash=binary_phash_str)

    def _match_images(self, image_name: str, phash: str) -> List[ImageMatch]:
        stmt = text("""
                    WITH search_hash AS (SELECT :phash ::bit(64) as phash),
                         candidates AS (SELECT i.id, i.phash
                                        FROM procurement.image_phashes i,
                                             search_hash s
                                        WHERE substring(i.phash from 1 for 16) = substring(s.phash from 1 for 16)
                                           OR substring(i.phash from 17 for 16) = substring(s.phash from 17 for 16)
                                           OR substring(i.phash from 33 for 16) = substring(s.phash from 33 for 16)
                                           OR substring(i.phash from 49 for 16) = substring(s.phash from 49 for 16))
                    SELECT id, (1.0 - (bit_count(phash # (SELECT phash FROM search_hash))::float / 64)) AS confidence
                    FROM candidates
                    WHERE bit_count(phash # (SELECT phash FROM search_hash)) <= 10
                    ORDER BY confidence DESC;
                    """)
        # noinspection PyTypeChecker
        rows = self.db.execute(stmt, {"phash": phash}).all()

        matches = []
        for row in rows:
            matches.append(ImageMatch(image_name=image_name, other_image_id=row[0], confidence=row[1]))
        return matches


ProcurementServiceDep = Annotated[ProcurementService, ProcurementService.dep()]
