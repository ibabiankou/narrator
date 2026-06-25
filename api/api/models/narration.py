import logging
import math
from pydantic import RootModel, BaseModel
from typing import List, Optional

from common_lib.models.tts import FragmentGroups, FragmentGroup

LOG = logging.getLogger(__name__)


class AudioTrack(BaseModel):
    name: str
    fragment_groups: FragmentGroups

    @classmethod
    def from_fragments(cls, fragments: List[FragmentGroup]) -> "AudioTrack":
        if fragments:
            first = fragments[0].root[0].id
            last = fragments[-1].root[-1].id
            name = f"{first}-{last}"
            # noinspection PyArgumentList
            return cls(name=name, fragment_groups=FragmentGroups(fragments))
        else:
            raise ValueError("No fragments")

    @staticmethod
    def split_into_tracks(
            fragment_groups: List[FragmentGroup],
            # This magic number is rough average from past data.
            # TODO: Move these magic numbers to configuration.
            target_track_duration_min: float = 3,
            chars_per_min=1000
    ) -> List["AudioTrack"]:
        if not fragment_groups:
            raise ValueError("No fragments")

        total_len = sum([group.length() for group in fragment_groups])
        num_tracks = max(1, math.floor(int(total_len / (target_track_duration_min * chars_per_min))))
        LOG.debug("Splitting %d fragment groups with total length %d into %d tracks",
                  len(fragment_groups), total_len, num_tracks)

        if num_tracks == 1:
            return [AudioTrack.from_fragments(fragment_groups)]
        else:
            result: List["AudioTrack"] = []
            avg_len = total_len / num_tracks
            remaining_len = avg_len
            current_track: List[FragmentGroup] = []
            for group in fragment_groups:
                if group.pause_only():
                    current_track.append(group)
                    continue

                if remaining_len <= 0:  # Got a full track
                    result.append(AudioTrack.from_fragments(current_track))
                    current_track = []
                    remaining_len += avg_len

                current_track.append(group)
                remaining_len -= group.length()

            if current_track:
                result.append(AudioTrack.from_fragments(current_track))

            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug("Actual number of tracks: %d", len(result))
                LOG.debug("Expected track length around: %d", avg_len)
                LOG.debug("Actual track lengths: %s",
                          [sum([g.length() for g in t.fragment_groups]) for t in result])

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
    def to_fragment_map(self) -> List:
        result = []
        for content_file in self.root:
            for nav_item in content_file.navigation_items:
                fragments = []
                for audio_track in nav_item.audio_tracks:
                    for fragment_group in audio_track.fragment_groups.root:
                        fragments.extend([f.formatted_id() for f in fragment_group.root])
                result.append({
                    "href": content_file.href,
                    "title": nav_item.title,
                    "fragments": fragments
                })
        return result
