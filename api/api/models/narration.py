import logging
from typing import List, Optional

import math
from pydantic import RootModel, BaseModel

from common_lib.models.tts import FragmentGroups, TextFragment, PauseFragment, Fragment

LOG = logging.getLogger(__name__)


class AudioTrack(BaseModel):
    name: str
    fragment_groups: FragmentGroups

    @classmethod
    def from_fragments(cls, fragments: List[List[Fragment]]) -> "AudioTrack":
        if fragments:
            first = fragments[0][0].id
            last = fragments[-1][-1].id
            name = f"{first}-{last}"
            # noinspection PyArgumentList
            return cls(name=name, fragment_groups=FragmentGroups(fragments))
        else:
            raise ValueError("No fragments")

    @staticmethod
    def split_into_tracks(
            fragment_groups: List[List[Fragment]],
            # This magic number is rough average from past data.
            # TODO: Move these magic numbers to configuration.
            target_track_duration_min: float = 3,
            chars_per_min=1000
    ) -> List["AudioTrack"]:
        if not fragment_groups:
            raise ValueError("No fragments")

        total_len = sum([AudioTrack.group_length(group) for group in fragment_groups])
        num_tracks = max(1, math.floor(int(total_len / (target_track_duration_min * chars_per_min))))
        LOG.debug("Splitting %d fragment groups with total length %d into %d tracks",
                  len(fragment_groups), total_len, num_tracks)

        if num_tracks == 1:
            return [AudioTrack.from_fragments(fragment_groups)]
        else:
            result: List["AudioTrack"] = []
            avg_len = total_len / num_tracks
            remaining_len = avg_len
            current_track: List[List[Fragment]] = []
            for group in fragment_groups:
                if AudioTrack.pause_only(group):
                    current_track.append(group)
                    continue

                if remaining_len <= 0:  # Got a full track
                    result.append(AudioTrack.from_fragments(current_track))
                    current_track = []
                    remaining_len += avg_len

                current_track.append(group)
                remaining_len -= AudioTrack.group_length(group)

            if current_track:
                result.append(AudioTrack.from_fragments(current_track))

            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug("Actual number of tracks: %d", len(result))
                LOG.debug("Expected track length around: %d", avg_len)
                LOG.debug("Actual track lengths: %s",
                          [sum([AudioTrack.group_length(g) for g in t.fragment_groups.root]) for t in result])

            return result

    @staticmethod
    def group_length(group: List[Fragment]) -> int:
        return sum([len(f.text) for f in group if isinstance(f, TextFragment)])

    @staticmethod
    def pause_only(group: List[Fragment]) -> bool:
        # Here I make an assumption that scene break is going to be a group with a single pause fragment.
        for f in group:
            if not isinstance(f, PauseFragment):
                return False
        return True


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
