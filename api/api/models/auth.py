import uuid
from typing import Annotated

from fastapi import Depends, Request, HTTPException
from pydantic import BaseModel


class User(BaseModel):
    id: uuid.UUID
    email: str

def get_current_user(request: Request):
    if "user" not in request.scope:
        raise HTTPException(
            status_code=401,
            detail="Unable to retrieve user from request",
        )
    return request.scope["user"]

UserDep = Annotated[User, Depends(get_current_user)]
