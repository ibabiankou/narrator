import os

import requests
from pydantic import BaseModel


class GeneratedAudio(BaseModel):
    content: bytes
    duration: float


class SpeechGenService:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = os.getenv("KOKORO_BASEURL")

    def phonemize(self, text: str) -> str:
        url = f"{self.base_url}/api/phonemize"
        request_json = {
            "text": text
        }
        response = self.session.post(url, json=request_json)
        return response.json()["phonemes"]

    def generate_from_phonemes(self, phonemes: str) -> GeneratedAudio:
        url = f"{self.base_url}/api/synthesize"
        response = self.session.post(url, json={"phonemes": phonemes})
        return GeneratedAudio(content=response.content, duration=float(response.headers["narrator-speech-duration"]))
