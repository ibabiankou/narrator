import logging
from io import BytesIO
from typing import Annotated, Optional

from blake3 import blake3
from pydantic import ValidationError
from sqlalchemy import select

from api.procurement.domain import IdMatch
from api.procurement.models import EpubFile, MetadataId
from common_lib.db import transactional
from common_lib.service import Service
from epub_lib import Epub

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
        normal_ids = set()
        id_matches = []
        for id in epub.package.metadata.identifier:
            # TODO: Do something smarter here.
            if id.value is None:
                LOG.debug("Got identifier without value. Skipping it.")
                continue
            normal_id = id.value.lower()
            metadata_id_maybe = self._find_metadata_id(normal_id)
            if metadata_id_maybe is not None:
                # If matched with a known ID, store the match information and continue.
                id_matches.append(IdMatch(matched_id=normal_id, other_book_id=metadata_id_maybe.source_file))
            else:
                # Only store normalized ID if it was not matched to an existing ID.
                normal_ids.add(normal_id)

        epub_file = EpubFile(file_name=filename,
                             file_hash=file_hash,
                             file_size_bytes=len(body.getbuffer()),
                             raw_metadata=metadata,
                             id_matches=id_matches
                             )
        self.db.add(epub_file)
        self.db.flush()
        self.db.add_all([MetadataId(source_file=epub_file.id, value=id) for id in normal_ids])

    def _find_file_by_hash(self, file_hash: str) -> Optional[EpubFile]:
        stmt = select(EpubFile).where(EpubFile.file_hash == file_hash)
        # noinspection PyTypeChecker
        return self.db.scalars(stmt).first()

    def _find_metadata_id(self, normal_id: str) -> Optional[MetadataId]:
        stmt = select(MetadataId).where(MetadataId.value == normal_id)
        # noinspection PyTypeChecker
        return self.db.scalars(stmt).first()


ProcurementServiceDep = Annotated[ProcurementService, ProcurementService.dep()]
