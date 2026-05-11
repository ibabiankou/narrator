import logging
from io import BytesIO
from typing import Annotated, Optional

from blake3 import blake3
from sqlalchemy import select

from api.procurement.models import EpubFile
from common_lib.db import transactional
from common_lib.service import Service

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

        epub_file = EpubFile(file_name=filename,
                             file_hash=file_hash,
                             file_size_bytes=len(body.getbuffer()))
        self.db.add(epub_file)


    def _find_file_by_hash(self, file_hash: str) -> Optional[EpubFile]:
        stmt = select(EpubFile).where(EpubFile.file_hash == file_hash)
        # noinspection PyTypeChecker
        return self.db.scalars(stmt).first()


ProcurementServiceDep = Annotated[ProcurementService, ProcurementService.dep()]
