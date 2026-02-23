from typing import Annotated, Optional

from sqlalchemy import select, update

from api import get_logger
from api.models import db
from api.models.db import DbSession
from common_lib.service import Service

LOG = get_logger(__name__)


class SettingsService(Service):
    def get_settings(self, kind: str) -> Optional[db.Settings]:
        with DbSession() as session:
            return session.scalar(select(db.Settings).where(db.Settings.kind == kind))

    def _add_settings(self, kind: str, data: dict):
        with DbSession() as session:
            session.add(db.Settings(kind=kind, data=data))
            session.commit()

    def _update_settings(self, kind: str, data: dict):
        with DbSession() as session:
            session.execute(update(db.Settings).where(db.Settings.kind == kind).values(data=data))
            session.commit()

    def patch_settings(self, kind: str, data: dict) -> Optional[db.Settings]:
        current = self.get_settings(kind)
        if current is None:
            self._add_settings(kind, data)
        else:
            self._update_settings(kind, recursive_patch(current.data, data))


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
