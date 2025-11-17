import logging
import sys
from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.models.models import get_session

SessionDep = Annotated[Session, Depends(get_session)]

def get_logger(name: str, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter("%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    return logger
