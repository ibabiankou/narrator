import numpy as np
from kokoro import KModel, KPipeline
from soundfile import SoundFile

from api import get_logger

LOG = get_logger(__name__)


class KokoroService:
    instance = None

    def __init__(self, lang_code: str = "a"):
        self.model = KModel()
        self.pipeline = KPipeline(lang_code, model=self.model, repo_id="hexgrad/Kokoro-82M")

    @classmethod
    def initialize(cls):
        if cls.instance is not None:
            LOG.warning("Initialize is called after already initialized")
        cls.instance = KokoroService()

    def phonemize(self, text: str):
        phonemes = []
        for result in self.pipeline(
            text=text,
            voice="am_adam",
            split_pattern= r'\n',
            model=None
        ):
            phonemes.append(result.phonemes)

        return "\n".join(phonemes)

    def synthesize(self, phonemes: str) -> bytes:
        file_name = "audio.wav"
        with SoundFile(file_name, mode="w", samplerate=24000, channels=1) as sf:
            chunks = phonemes.split("\n")
            for chunk in chunks:
                for result in self.pipeline.generate_from_tokens(
                        tokens=chunk,
                        voice="am_adam"
                ):
                    sf.write(result.audio)
                sf.write(self._silence(0.25))

        with open(file_name, "rb") as f:
            return f.read()

    def _silence(self, duration_s: float):
        silence_samples = int(duration_s * 24000)  # 24kHz sample rate
        silence_audio = np.zeros(silence_samples, dtype=np.int16)
        return silence_audio
