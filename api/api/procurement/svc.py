import logging
from io import BytesIO
from typing import Annotated, Optional

from blake3 import blake3
from sqlalchemy import select

from api.procurement.domain import IdMatch
from api.procurement.models import EpubFile, MetadataId
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
        epub = Epub(body)
        metadata: dict = epub.package.metadata.model_dump(exclude_none=True)

        # search for ID matches
        ids_to_store = {}
        id_matches = []
        for id in epub.package.metadata.identifier:
            if id.value is None:
                LOG.debug("Skipping identifier without value.")
                continue

            id_type, id_value = normalize_identifier(id.value)
            if id_type == "calibre":
                LOG.debug("Skipping calibre ID, assuming they are not global. Book: '%s', ID: '%s'",
                          filename, id_value)
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

        epub_file = EpubFile(file_name=filename,
                             file_hash=file_hash,
                             file_size_bytes=len(body.getbuffer()),
                             raw_metadata=metadata,
                             id_matches=id_matches
                             )
        self.db.add(epub_file)
        self.db.flush()

        for i in ids_to_store.values():
            i.source_file = epub_file.id
        self.db.add_all(ids_to_store.values())

    def _find_file_by_hash(self, file_hash: str) -> Optional[EpubFile]:
        stmt = select(EpubFile).where(EpubFile.file_hash == file_hash)
        # noinspection PyTypeChecker
        return self.db.scalars(stmt).first()

    def _find_metadata_id(self, id_type: str, id_value: str) -> Optional[MetadataId]:
        stmt = select(MetadataId).where(MetadataId.type == id_type).where(MetadataId.value == id_value)
        # noinspection PyTypeChecker
        return self.db.scalars(stmt).first()


ProcurementServiceDep = Annotated[ProcurementService, ProcurementService.dep()]
