import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Any, Literal, Union, Annotated

from pydantic import BaseModel, RootModel, field_serializer, field_validator, Field


class FragmentType(str, Enum):
    TEXT = "text"
    PAUSE = "pause"


class FragmentId(BaseModel):
    id: int

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


class FragmentBase(FragmentId):
    type: FragmentType
    visited_ids: List[str] = []


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


@dataclass
class Token:
    NORM_PATTERN = re.compile(r'\W+')

    # A slice of the text from the html.
    raw_text: str
    # The same slice, but cleaned up for TTS.
    tts_text: str
    # The same slice, but normalized for comparison during reconstruction.
    normalized_text: str

    length: int

    def __init__(self, text: str):
        self.raw_text = text
        # TODO: Do a smarter cleanup.
        self.tts_text = re.sub(r'\s+', ' ', text)

        self.normalized_text = self.normalize(text)
        self.length = len(self.normalized_text)

    @staticmethod
    def normalize(text: str):
        return Token.NORM_PATTERN.sub('', text).lower()

    def ensure_ends_with_punctuation(self):
        """Adds a period to the end of the tts_text unless it's already ends with some punctuation."""
        if self.tts_text:
            if self.tts_text[-1] not in ".!?":
                self.tts_text += '.'

    def __str__(self):
        return self.normalized_text
    def __repr__(self):
        return self.__str__()




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


class FragmentDuration(FragmentId):
    duration: float


class TrackManifest(BaseModel):
    audio_key: str
    track_name: str
    size_bytes: int
    timeline: List[FragmentDuration]
