import os

import requests

class KokoroClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = os.getenv("KOKORO_BASEURL")

    def phonemize(self, text: str) -> str:
        url = f"{self.base_url}/dev/phonemize"
        request_json = {
            "text": text,
            "language": "a"
        }
        response = self.session.post(url, json=request_json)
        return response.json()["phonemes"]

    def generate_from_phonemes(self, phonemes: str) -> bytes:
        url = f"{self.base_url}/dev/generate_from_phonemes"
        request_json = {
            "phonemes": phonemes,
            "voice": "am_adam",
        }
        response = self.session.post(url, json=request_json)
        return response.content
