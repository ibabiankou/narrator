import logging

from api.speechgen import SpeechGenService
from common_lib.models.tts import TextFragment, PauseFragment, FragmentList

LOG = logging.getLogger(__name__)

speechgen = SpeechGenService(None)


class TestSpeechGenService:
    def test_fragment(self, project_dist_path):
        frag = TextFragment(id=1, text="Hello my friend. How are you doing tonight?")
        audio_np, np_duration = speechgen._narrate_fragment(frag, "am_michael")

        audio_bytes, aac_duration = speechgen._encode_audio(audio_np)
        with open(project_dist_path / "test_fragment.aac", "wb") as f:
            f.write(audio_bytes.getvalue())

    def test_fragments(self, project_dist_path):
        fragments = [
            TextFragment(id=1, text="Hello my friend. How are you doing tonight?"),
            PauseFragment(id=2, duration=1.5),
            TextFragment(id=3, text="I'm fine, thank you. How is life treating you?")
        ]
        audio_np, durations = speechgen._narrate_fragments(FragmentList(fragments), "am_michael")
        LOG.info("Durations. sum: %s\n%s", sum([d.duration for d in durations]), durations)

        audio_bytes, aac_duration = speechgen._encode_audio(audio_np)
        LOG.info("AAC duration: %s", aac_duration)
        with open(project_dist_path / "test_fragments.aac", "wb") as f:
            f.write(audio_bytes.getvalue())
