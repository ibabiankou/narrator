import logging
import uuid
from dataclasses import dataclass
from typing import Annotated, Optional

from sqlalchemy import select, update

from api.models import db
from common_lib.db import transactional
from common_lib.service import Service

LOG = logging.getLogger(__name__)

@dataclass
class SystemSettings:
    speech_generation_enabled: bool = False


# noinspection PyTypeChecker
class SettingsService(Service):
    def __init__(self, **kwargs):
        self.system_user_id = uuid.UUID("7e8fdd19-af4f-41b1-a43a-e00b8bdeefb4")

    @transactional
    def get_settings(self, user_id: uuid.UUID, kind: str) -> dict:
        settings = self._load_settings(user_id, kind)
        return settings.data if settings is not None else default_settings(kind)

    def get_system_settings(self) -> SystemSettings:
        data_dict = self.get_settings(self.system_user_id, "system")
        return SystemSettings(**data_dict)

    def _load_settings(self, user_id: uuid.UUID, kind: str) -> Optional[db.Settings]:
        stmt = select(db.Settings).where(db.Settings.user_id == user_id).where(db.Settings.kind == kind)
        return self.db.scalar(stmt)

    def _add_settings(self, user_id: uuid.UUID, kind: str, data: dict):
        self.db.add(db.Settings(user_id=user_id, kind=kind, data=data))

    def _update_settings(self, user_id: uuid.UUID, kind: str, data: dict):
        stmt = update(db.Settings).where(db.Settings.user_id == user_id).where(db.Settings.kind == kind).values(data=data)
        self.db.execute(stmt)

    @transactional
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
