from fastapi import APIRouter, HTTPException

from api.models.auth import UserDep, User
from api.services.settings import SettingsServiceDep

settings_router = APIRouter(tags=["Settings API"])


@settings_router.get("/{kind}")
def get_settings(kind: str,
                 user: UserDep,
                 settings_svc: SettingsServiceDep) -> dict:
    validate_request(kind, user)
    return settings_svc.get_settings(user.id, kind)


def validate_request(kind: str, user: User):
    if kind not in ["system", "user_preferences"]:
        raise HTTPException(status_code=400, detail=f"Unsupported kind of settings: {kind}")

    if kind == "system" and not user.has_any_role(["admin"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


@settings_router.patch("/{kind}")
def patch_settings(kind: str,
                   payload: dict,
                   user: UserDep,
                   settings_svc: SettingsServiceDep) -> dict:
    validate_request(kind, user)
    settings_svc.patch_settings(user.id, kind, payload)
    return settings_svc.get_settings(user.id, kind)
