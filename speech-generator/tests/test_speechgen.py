import logging

from api.speechgen import SpeechGenService
from common_lib.models.tts import TextFragment

LOG = logging.getLogger(__name__)

speechgen = SpeechGenService(None)


class TestSpeechGenService:
    def test_fragments(self, project_dist_path):
        fragments = [
            TextFragment(id=1, text="Per the Mined Material Reclamation act along with subsection 35 of the Indigenous Planetary "),
            TextFragment(id=2, text="Species Protection Act, any surviving humans will be given the opportunity to reclaim "),
            TextFragment(id=3, text="their lost matter. The Borant Corporation, having been assigned regency over this solar system, "),
            TextFragment(id=4, text="is allowed to choose the manner of this reclamation, and they have chosen option 3, also "),
            TextFragment(id=5, text="known as the 18-Level World Dungeon. The Borant Corporation retains all rights to broadcast, "),
            TextFragment(id=6, text="exploit, and otherwise control all aspects of the World Dungeon and will remain in control "),
            TextFragment(id=7, text="as long as they adhere to Syndicate regulations regarding world resource reclamation."),
        ]
        audio_np, durations = speechgen._narrate_fragments(fragments, "am_michael")
        LOG.info("Durations. sum: %s\n%s", sum([d.duration for d in durations]), durations)

        audio_bytes, aac_duration = speechgen._encode_audio(audio_np)
        LOG.info("AAC duration: %s", aac_duration)
        with open(project_dist_path / "test_fragments.aac", "wb") as f:
            f.write(audio_bytes.getvalue())
