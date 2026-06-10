import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Any, Literal, Union, Annotated

import unicodedata
from pydantic import BaseModel, RootModel, field_serializer, field_validator, Field

LOG = logging.getLogger(__name__)


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


class FragmentGroup(RootModel[List[Fragment]]):
    def length(self):
        return sum([len(f.text) for f in self.root if isinstance(f, TextFragment)])

    def pause_only(self) -> bool:
        # Here I make an assumption that scene break is going to be a group with a single pause fragment.
        for f in self.root:
            if not isinstance(f, PauseFragment):
                return False
        return True


class FragmentGroups(RootModel[List[FragmentGroup]]):

    def remove_all_by_visited_id(self, idref: Optional[str]) -> List[FragmentGroup]:
        """Removes all groups having the given idref among visited_ids. Returns the list of removed groups.

        idref: is the fragment ID from the ToC navigation item. We assume it's not possible for one group to be split
         between ToC items.
        """
        if idref is None:
            removed = self.root
            self.root = []
            return removed

        removed = []
        remaining = []
        for group in self.root:
            # If any of the fragments in the group has the idref, remove it.
            remove_group = False
            for frag in group.root:
                # Assumption here is that all fragments in the group belong to the same navigation idref.
                if idref in frag.visited_ids:
                    remove_group = True
                    break

            if remove_group:
                removed.append(group)
            else:
                remaining.append(group)

        self.root = remaining
        return removed

    def all_fragment_ids(self) -> List[str]:
        """Returns a list of all fragment IDs in the groups."""
        return [f.formatted_id() for group in self.root for f in group.root]

    def flatten(self) -> List[Fragment]:
        return [f for group in self.root for f in group.root]


@dataclass
class Token:
    NORM_PATTERN = re.compile(r'\W+')
    PUNCTUATION_MAP = str.maketrans({
        # Left and right curly double quotes -> standard double quote
        '“': '"', '”': '"', '„': '"', '‟': '"', '«': '"', '»': '"',
        # Left and right curly single quotes / apostrophes -> standard single quote
        '‘': "'", '’': "'", '‚': "'", '‛': "'", '‹': "'", '›': "'", '`': "'", '´': "'", '′': "'",
        # Various dashes (en-dash, em-dash, horizontal bar, figure dash) -> standard hyphen/minus
        '–': '-', '—': '-', '―': '-', '‒': '-', '‑': '-', '−': '-',
    })
    TTS_CLEANUP_RULES = [
        (re.compile(r'\s+'), ' '),
        (re.compile(r'[!]{2,}'), '!'),
        (re.compile(r'[?]{2,}'), '?'),
        (re.compile(r'\.(\s*\.){2,}'), '…'),
        (re.compile(r'[\u2060]'), ''),
    ]

    # A slice of the text from the html.
    raw_text: str
    # The same slice, but cleaned up for TTS.
    _tts_text: str
    # The same slice, but normalized for comparison during reconstruction.
    normalized_text: str

    length: int
    # Flag indicating punctuation should be added at the end of the text, if not already present.
    add_punctuation_in_tts: bool = False

    def __init__(self, text: str):
        self.raw_text = text
        self._tts_text = self._clean_for_tts(text)

        self.normalized_text = self.normalize(text)
        self.length = len(self.normalized_text)

    @staticmethod
    def normalize(text: str):
        return Token.NORM_PATTERN.sub('', text).lower()

    def tts_text(self):
        if not self.add_punctuation_in_tts:
            return self._tts_text

        if self._tts_text and self._tts_text[-1].isspace():
            return self._add_punctuation(self._tts_text.rstrip()) + " "
        else:
            return self._add_punctuation(self._tts_text)

    def _add_punctuation(self, text: str):
        if text and text[-1] not in ":;,.!?":
            return text + "."
        return text

    def starts_with_whitespace(self):
        s = self.raw_text
        return bool(s and s[0].isspace())

    def ends_with_whitespace(self):
        s = self.raw_text
        return bool(s and s[-1].isspace())

    def __str__(self):
        return f"'{self.raw_text}'"

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def _clean_for_tts(text: str) -> str:
        text = unicodedata.normalize('NFKC', text)
        for regex, replacement in Token.TTS_CLEANUP_RULES:
            text = regex.sub(replacement, text)
        text = text.translate(Token.PUNCTUATION_MAP)
        return text


class FragmentGroupsBuilder(BaseModel):
    current_id: int = 0
    fragment_groups: List[List[Fragment]] = []
    current_group: Optional[List[Fragment]] = None

    def next_id(self):
        next_id = self.current_id
        self.current_id += 1
        return next_id

    def next_group(self):
        """Starts a new group of fragments."""
        if self.current_group and len(self.current_group) == 0:
            LOG.warning("Got request to start a new group, but the current group is empty. Doing nothing.")
            return

        self.current_group = []
        # noinspection PyTypeChecker
        self.fragment_groups.append(self.current_group)

    def add_pause(self, duration: float, visited_ids: List[str]) -> Fragment:
        frag = PauseFragment(id=self.next_id(), duration=duration, visited_ids=visited_ids)
        self.current_group.append(frag)
        return frag

    def current_group_size(self):
        return 0 if self.current_group is None else len(self.current_group)

    def build(self):
        # noinspection PyArgumentList
        return FragmentGroups(self.fragment_groups)

    def add_tokens(self, tokens: List[Token], visited_ids: List[str]) -> Fragment:
        text = "".join([t.tts_text() for t in tokens])
        frag = TextFragment(id=self.next_id(), text=text, visited_ids=visited_ids)
        self.current_group.append(frag)
        return frag


class FragmentDuration(FragmentId):
    duration: float


class TrackManifest(BaseModel):
    audio_key: str
    track_name: str
    size_bytes: int
    timeline: List[FragmentDuration]
