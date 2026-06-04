import re
from enum import Enum
from typing import List, Optional, Any, Literal, Union, Annotated

from pydantic import BaseModel, RootModel, field_serializer, field_validator, Field


class FragmentType(str, Enum):
    TEXT = "text"
    PAUSE = "pause"


class FragmentBase(BaseModel):
    id: int
    type: FragmentType
    visited_ids: List[str] = []

    @field_serializer('id')
    def serialize_id(self, id_val: int) -> str:
        """Converts the internal integer to 'n-X' when dumping to dict/JSON."""
        return f"n-{id_val}"

    def formatted_id(self):
        return self.serialize_id(self.id)

    @field_validator('id', mode='before')
    @classmethod
    def deserialize_id(cls, value: Any) -> int:
        """Intercepts the 'n-X' string and extracts the integer before validation."""
        if isinstance(value, str):
            # Use regex to match the pattern 'n-digits'
            match = re.match(r"^n-(\d+)$", value)
            if match:
                return int(match.group(1))
            else:
                raise ValueError("Fragment ID must be in the format 'n-X' (e.g., 'n-42')")

        # If it's already an integer, just let it pass through
        return value


class TextFragment(FragmentBase):
    type: Literal[FragmentType.TEXT] = FragmentType.TEXT
    text: str


class PauseFragment(FragmentBase):
    type: Literal[FragmentType.PAUSE] = FragmentType.PAUSE
    duration: float


Fragment = Annotated[
    Union[TextFragment, PauseFragment],
    Field(discriminator='type')
]


class FragmentList(RootModel[List[Fragment]]):
    def remove_all_by_visited_id(self, idref: Optional[str]) -> List[Fragment]:
        """Removes all fragments having the given idref among visited_ids.
        Returns the list of removed fragments."""
        if idref is None:
            removed = self.root
            self.root = []
            return removed

        removed = [f for f in self.root if idref in f.visited_ids]
        self.root = [f for f in self.root if idref not in f.visited_ids]
        return removed


class FragmentListBuilder(BaseModel):
    current_id: int = 0
    fragments: List[Fragment] = []

    def next_id(self):
        next_id = self.current_id
        self.current_id += 1
        return next_id

    def add_pause(self, duration: float, visited_ids: List[str]) -> Fragment:
        frag = PauseFragment(id=self.next_id(), duration=duration, visited_ids=visited_ids)
        self.fragments.append(frag)
        return frag

    def add_text(self, text: str, visited_ids: List[str]) -> Fragment:
        frag = TextFragment(id=self.next_id(), text=text, visited_ids=visited_ids)
        self.fragments.append(frag)
        return frag

    def build(self):
        # noinspection PyArgumentList
        return FragmentList(self.fragments)
