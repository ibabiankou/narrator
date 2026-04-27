import logging
from typing import Annotated

from common_lib.db import transactional
from common_lib.service import Service

LOG = logging.getLogger(__name__)


# noinspection PyTypeChecker
class OpenlibraryService(Service):
    def __init__(self, **kwargs):
        pass

    @transactional
    def edition_by_isbn(self, isbn: str):
        pass


OpenlibraryServiceDep = Annotated[OpenlibraryService, OpenlibraryService.dep()]
