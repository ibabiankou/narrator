import logging
from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.models.db import get_session

SessionDep = Annotated[Session, Depends(get_session)]

def get_logger(name: str, level=logging.INFO):
    return logging.getLogger(name)
