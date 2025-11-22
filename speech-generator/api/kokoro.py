from io import BytesIO

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

    def synthesize(self, phonemes: str, voice: str = "am_adam", speed: float = 1.1) -> dict:
        audio_buf = BytesIO()
        audio_format = "mp3"
        with SoundFile(audio_buf, mode="w", format=audio_format, samplerate=24000, channels=1, compression_level=0.99) as sf:
            chunks = phonemes.split("\n")
            for chunk in chunks:
                if not chunk.strip():
                    continue
                for result in self.pipeline.generate_from_tokens(tokens=chunk, voice=voice, speed=speed):
                    sf.write(result.audio)
                sf.write(self._silence(0.25))
        audio_buf.seek(0)
        return {
            "content": audio_buf.read(),
            "content_type": f"audio/{audio_format}",
        }

    def _silence(self, duration_s: float):
        return np.zeros(int(duration_s * 24000), dtype=np.int16) # 24kHz sample rate
