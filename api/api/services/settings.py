import uuid
from dataclasses import dataclass
from typing import Annotated, Optional

from sqlalchemy import select, update

from api import get_logger
from api.models import db
from api.models.db import DbSession
from common_lib.service import Service

LOG = get_logger(__name__)

@dataclass
class SystemSettings:
    speech_generation_enabled: bool = False

class SettingsService(Service):
    def __init__(self):
        self.system_user_id = uuid.UUID("7e8fdd19-af4f-41b1-a43a-e00b8bdeefb4")

    def get_settings(self, user_id: uuid.UUID, kind: str) -> dict:
        settings = self._load_settings(user_id, kind)
        return settings.data if settings is not None else default_settings(kind)

    def get_system_settings(self) -> SystemSettings:
        data_dict = self.get_settings(self.system_user_id, "system")
        return SystemSettings(**data_dict)

    def _load_settings(self, user_id: uuid.UUID, kind: str) -> Optional[db.Settings]:
        with DbSession() as session:
            stmt = select(db.Settings).where(db.Settings.user_id == user_id).where(db.Settings.kind == kind)
            return session.scalar(stmt)

    def _add_settings(self, user_id: uuid.UUID, kind: str, data: dict):
        with DbSession() as session:
            session.add(db.Settings(user_id=user_id, kind=kind, data=data))
            session.commit()

    def _update_settings(self, user_id: uuid.UUID, kind: str, data: dict):
        with DbSession() as session:
            stmt = update(db.Settings).where(db.Settings.user_id == user_id).where(db.Settings.kind == kind).values(data=data)
            session.execute(stmt)
            session.commit()

    def patch_settings(self, user_id: uuid.UUID, kind: str, data: dict):
        current = self._load_settings(user_id, kind)
        if current is None:
            self._add_settings(user_id, kind, recursive_patch(default_settings(kind), data))
        else:
            self._update_settings(user_id, kind, recursive_patch(current.data, data))


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

def recursive_patch(target: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if value is None:
            target.pop(key, None)
        elif isinstance(value, dict):
            if isinstance(target.get(key), dict):
                recursive_patch(target[key], value)
            else:
                target[key] = value
        else:
            target[key] = value
    return target


SettingsServiceDep = Annotated[SettingsService, SettingsService.dep()]
