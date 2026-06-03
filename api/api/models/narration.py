import logging
from typing import List, Optional

import math
from pydantic import RootModel, BaseModel

from epub_lib.model.tts import FragmentList, TextFragment, PauseFragment


LOG = logging.getLogger(__name__)


class AudioTrack(BaseModel):
    name: str
    fragments: FragmentList

    @classmethod
    def from_fragments(cls, fragments: FragmentList):
        text_fragments = [f for f in fragments if isinstance(f, TextFragment)]
        if text_fragments:
            first = text_fragments[0].id
            last = text_fragments[-1].id
            name = f"{first}-{last}"
            return cls(name=name, fragments=fragments)
        else:
            raise ValueError("No fragments")

    @staticmethod
    def split_into_tracks(
            fragments: FragmentList,
            # This magic number is rough average from past data.
            # TODO: Move these magic numbers to configuration.
            target_track_duration_min: float = 3,
            chars_per_min=1000
    ) -> List["AudioTrack"]:

        total_len = sum([len(f.text) for f in fragments if isinstance(f, TextFragment)])
        num_tracks = max(1, math.floor(int(total_len / (target_track_duration_min * chars_per_min))))
        LOG.debug("Splitting %d fragments with total length %d into %d tracks",
                 len(fragments), total_len, num_tracks)

        if num_tracks == 1:
            return [AudioTrack.from_fragments(fragments)]
        else:
            result = []
            avg_len = total_len / num_tracks
            remaining_len = total_len
            current_track_fragments = []
            for frag in fragments:
                if isinstance(frag, PauseFragment):
                    current_track_fragments.append(frag)
                    continue

                if remaining_len <= 0:  # Got a full track
                    # noinspection PyArgumentList
                    result.append(AudioTrack.from_fragments(FragmentList(current_track_fragments)))
                    current_track_fragments = []
                    remaining_len += avg_len
                    continue

                if isinstance(frag, TextFragment):
                    current_track_fragments.append(frag)
                    remaining_len -= len(frag.text)
                    continue

                raise ValueError(f"This should never happen... :)")

            if current_track_fragments:
                # noinspection PyArgumentList
                result.append(AudioTrack.from_fragments(FragmentList(current_track_fragments)))

            LOG.debug("Actual number of tracks: %d", len(result))
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
