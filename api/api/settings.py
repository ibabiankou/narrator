from fastapi import APIRouter, HTTPException

from api.services.settings import SettingsServiceDep

settings_router = APIRouter(tags=["Settings API"])


@settings_router.get("/{kind}")
def get_settings(kind: str, settings_svc: SettingsServiceDep) -> dict:
    validate_kind(kind)
    return settings_svc.get_settings(kind)


def validate_kind(kind: str):
    if kind not in ["system", "user_preferences"]:
        raise HTTPException(status_code=400, detail=f"Unsupported kind of settings: {kind}")


@settings_router.patch("/{kind}")
def patch_settings(kind: str,
                   payload: dict,
                   settings_svc: SettingsServiceDep) -> dict:
    validate_kind(kind)
    settings_svc.patch_settings(kind, payload)
    return settings_svc.get_settings(kind)
