import uuid

from pydantic import RootModel


class ID(RootModel):
    root: uuid.UUID
