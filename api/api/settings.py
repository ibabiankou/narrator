from fastapi import APIRouter

from api.services.settings import SettingsServiceDep

settings_router = APIRouter(tags=["Settings API"])


@settings_router.get("/{kind}")
def get_settings(kind: str, settings_svc: SettingsServiceDep) -> dict:
    settings = settings_svc.get_settings(kind)

    if settings is None:
        return default_settings(kind)

    return settings.data


def default_settings(kind: str):
    if kind == "system":
        return {}
    if kind == "user_preferences":
        return {
            # light / dark
            "theme": "light",
            "playback_rate": 1,
            "auto_scroll": True,
            "text_size": 16,
            # text / pages / both
            "viewer_mode": "text"
        }

    raise ValueError(f"Unsupported kind of settings: {kind}")


@settings_router.patch("/{kind}")
def patch_settings(kind: str,
                   payload: dict,
                   settings_svc: SettingsServiceDep) -> dict:
    settings_svc.patch_settings(kind, payload)
    return settings_svc.get_settings(kind).data
