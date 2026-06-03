from enum import Enum
from typing import List

from pydantic import BaseModel, RootModel


type Fragment = TextFragment | PauseFragment


class FragmentType(str, Enum):
    TEXT = "text"
    PAUSE = "pause"


class FragmentBase(BaseModel):
    id: str
    type: FragmentType
    visited_ids: List[str]


class TextFragment(FragmentBase):
    type: FragmentType = FragmentType.TEXT
    text: str


class PauseFragment(FragmentBase):
    type: FragmentType = FragmentType.PAUSE
    duration: float


class FragmentList(RootModel[List[Fragment]]):
    pass
