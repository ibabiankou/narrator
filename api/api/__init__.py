from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.models.models import get_session

SessionDep = Annotated[Session, Depends(get_session)]
