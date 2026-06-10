import logging

from api.models.narration import AudioTrack
from common_lib.models.tts import TextFragment, FragmentGroup

LOG = logging.getLogger(__name__)


class TestAudioTrack:
    def test_split(self):
        # noinspection PyArgumentList
        fragment_groups = [
            FragmentGroup([TextFragment(id=1, text="Hello my friend.", )]),
            FragmentGroup([TextFragment(id=2, text="Is there anything I can do for you?", )]),
            FragmentGroup([TextFragment(id=3, text="I think it's going to be great.", )]),
        ]

        tracks = AudioTrack.split_into_tracks(fragment_groups, 2, 20)

        assert len(tracks) == 2
        assert tracks[0].name == "1-2"
        assert tracks[1].name == "3-3"

    def test_split_one(self):
        # noinspection PyArgumentList
        fragment_groups = [
            FragmentGroup([TextFragment(id=1, text="Hello my friend.", )]),
            FragmentGroup([TextFragment(id=2, text="Is there anything I can do for you?", )]),
        ]

        tracks = AudioTrack.split_into_tracks(fragment_groups, 2, 200)

        assert len(tracks) == 1
        assert tracks[0].name == "1-2"

    def test_dont_split_group(self):
        # noinspection PyArgumentList
        fragment_groups = [
            FragmentGroup([
                TextFragment(id=1, text="Hello my friend.", ),
                TextFragment(id=2, text="Is there anything I can do for you?", ),
                TextFragment(id=3, text="I think it's going to be great.", )
            ]),
        ]

        tracks = AudioTrack.split_into_tracks(fragment_groups, 2, 10)

        assert len(tracks) == 1
        assert tracks[0].name == "1-3"
