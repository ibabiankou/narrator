import logging

from api.models.narration import AudioTrack
from common_lib.models.tts import TextFragment

LOG = logging.getLogger(__name__)

class TestAudioTrack:
    def test_split(self):
        fragments = [
            TextFragment(id=1, text="Hello my friend.", ),
            TextFragment(id=2, text="Is there anything I can do for you?", ),
            TextFragment(id=3, text="I think it's going to be great.", ),
        ]

        tracks = AudioTrack.split_into_tracks(fragments, 2, 20)

        assert len(tracks) == 2
        assert tracks[0].name == "1-2"
        assert tracks[1].name == "3-3"

    def test_split_one(self):
        fragments = [
            TextFragment(id=1, text="Hello my friend.", ),
            TextFragment(id=2, text="Is there anything I can do for you?", ),
        ]

        tracks = AudioTrack.split_into_tracks(fragments, 2, 200)

        assert len(tracks) == 1
        assert tracks[0].name == "1-2"
