import logging
from typing import List, Optional

import math
from pydantic import RootModel, BaseModel

from common_lib.models.tts import FragmentList, TextFragment, PauseFragment, Fragment

LOG = logging.getLogger(__name__)


class AudioTrack(BaseModel):
    name: str
    fragments: FragmentList

    @classmethod
    def from_fragments(cls, fragments: List[Fragment]) -> "AudioTrack":
        if fragments:
            first = fragments[0].id
            last = fragments[-1].id
            name = f"{first}-{last}"
            # noinspection PyArgumentList
            return cls(name=name, fragments=FragmentList(fragments))
        else:
            raise ValueError("No fragments")

    @staticmethod
    def split_into_tracks(
            fragments: List[Fragment],
            # This magic number is rough average from past data.
            # TODO: Move these magic numbers to configuration.
            target_track_duration_min: float = 3,
            chars_per_min=1000
    ) -> List["AudioTrack"]:
        if not fragments:
            raise ValueError("No fragments")

        total_len = sum([len(f.text) for f in fragments if isinstance(f, TextFragment)])
        num_tracks = max(1, math.floor(int(total_len / (target_track_duration_min * chars_per_min))))
        LOG.debug("Splitting %d fragments with total length %d into %d tracks",
                 len(fragments), total_len, num_tracks)

        if num_tracks == 1:
            return [AudioTrack.from_fragments(fragments)]
        else:
            result: List["AudioTrack"] = []
            avg_len = total_len / num_tracks
            remaining_len = avg_len
            current_track_fragments: List[Fragment] = []
            for frag in fragments:
                if isinstance(frag, PauseFragment):
                    current_track_fragments.append(frag)
                    continue

                if remaining_len <= 0:  # Got a full track
                    result.append(AudioTrack.from_fragments(current_track_fragments))
                    current_track_fragments = []
                    remaining_len += avg_len

                if isinstance(frag, TextFragment):
                    current_track_fragments.append(frag)
                    remaining_len -= len(frag.text)
                    continue

                raise ValueError(f"This should never happen... :)")

            if current_track_fragments:
                result.append(AudioTrack.from_fragments(current_track_fragments))

            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug("Actual number of tracks: %d", len(result))
                LOG.debug("Expected track length around: %d", avg_len)
                LOG.debug("Actual track lengths: %s",
                          [sum([len(f.text) for f in t.fragments.root if isinstance(f, TextFragment)]) for t in result])

            return result


class NavigationItem(BaseModel):
    idref: Optional[str] = None
    title: str
    narrate: bool = True
    audio_tracks: List[AudioTrack] = []


class ContentFile(BaseModel):
    href: str
    title: Optional[str] = None
    epub_types: List[str] = []
    navigation_items: List[NavigationItem] = []


class NarrationManifest(RootModel[List[ContentFile]]):
    pass
