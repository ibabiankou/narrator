import uuid
from typing import Annotated, Dict, Any

from fastapi import Depends, Request, HTTPException
from pydantic import BaseModel


class User(BaseModel):
    id: uuid.UUID
    email: str
    realm_roles: list[str]

    def has_any_role(self, roles: list[str]) -> bool:
        return any(role in self.realm_roles for role in roles)


async def map_user(userinfo: Dict[str, Any]) -> User:
    return User(
        id=userinfo["sub"],
        email=userinfo["email"],
        realm_roles=userinfo["realm_access"]["roles"]
    )


def get_current_user(request: Request):
    if "user" not in request.scope:
        raise HTTPException(
            status_code=401,
            detail="Unable to retrieve user from request",
        )
    return request.scope["user"]


UserDep = Annotated[User, Depends(get_current_user)]


def user_with_roles(allowed_roles: list):
    def role_checker(user: UserDep):
        if not user.has_any_role(allowed_roles):
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )
        return user

    return role_checker


AdminUser = Annotated[User, Depends(user_with_roles(["admin"]))]
