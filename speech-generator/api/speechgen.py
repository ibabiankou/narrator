import os
from io import BytesIO
from typing import Annotated

import boto3
import numpy as np
from botocore.exceptions import ClientError
from kokoro import KModel, KPipeline
from soundfile import SoundFile

from api import get_logger
from common_lib import RMQClientDep
from common_lib.models import rmq
from common_lib.service import Service

LOG = get_logger(__name__)


class SpeechGenService(Service):
    def __init__(self, rmq_client: RMQClientDep, lang_code: str = "a"):
        self.rmq_client = rmq_client
        self.model = KModel()
        self.speech_pipeline = KPipeline(lang_code, model=self.model, repo_id="hexgrad/Kokoro-82M")
        self.phonemes_pipeline = KPipeline(lang_code, model=False, repo_id="hexgrad/Kokoro-82M")

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT"),
            region_name=os.getenv("S3_REGION"),
            aws_access_key_id=os.getenv("S3_ACCESS"),
            aws_secret_access_key=os.getenv("S3_SECRET")
        )
        self.bucket_name = os.getenv("S3_BUCKET", "narrator")

    def phonemize(self, text: str, voice: str = "am_adam"):
        phonemes = []
        for result in self.phonemes_pipeline(
                text=text,
                voice=voice,
                split_pattern=r'\n',
                model=None
        ):
            phonemes.append(result.phonemes)

        return "\n".join(phonemes)

    def handle_phonemize_msg(self, payload: rmq.PhonemizeText):
        LOG.debug("Converting text into phonemes for track %s.", payload.track_id)
        phonemes = self.phonemize(payload.text)
        payload = rmq.PhonemesResponse(book_id=payload.book_id, section_id=payload.section_id,
                                       track_id=payload.track_id, phonemes=phonemes)
        self.rmq_client.publish(routing_key="phonemes", payload=payload)

    def synthesize(self, phonemes: str, voice: str = "am_adam", speed: float = 1.1) -> dict:
        audio_buf = BytesIO()
        audio_format = "mp3"
        with SoundFile(audio_buf, mode="w", format=audio_format, samplerate=24000, channels=1,
                       compression_level=0.5) as sf:
            chunks = phonemes.split("\n")
            for chunk in chunks:
                if not chunk.strip():
                    continue
                for result in self.speech_pipeline.generate_from_tokens(tokens=chunk, voice=voice, speed=speed):
                    sf.write(result.audio)
                sf.write(self._silence(0.1))

            audio_buf.seek(0)
            return {
                "content": audio_buf.read(),
                "duration": float(sf.frames) / sf.samplerate,
                "content_type": f"audio/{audio_format}",
            }

    def _silence(self, duration_s: float):
        return np.zeros(int(duration_s * 24000), dtype=np.int16)  # 24kHz sample rate

    def handle_synthesize_msg(self, payload: rmq.SynthesizeSpeech):
        LOG.debug("Synthesizing speech for track %s.", payload.track_id)
        result = self.synthesize(payload.phonemes)
        self._upload_file(payload.file_path, result.get("content_type"), result.get("content"))
        payload = rmq.SpeechResponse(book_id=payload.book_id, section_id=payload.section_id, track_id=payload.track_id,
                                     file_path=payload.file_path, duration=result.get("duration"))
        self.rmq_client.publish(routing_key="speech", payload=payload)

    def _upload_file(self, remote_file_path: str, content_type: str, body: bytes):
        try:
            self.s3_client.put_object(
                Body=body,
                Bucket=self.bucket_name,
                Key=remote_file_path,
                ContentType=content_type)
        except ClientError as e:
            LOG.error(e)
            raise e

SpeechGenServiceDep = Annotated[SpeechGenService, SpeechGenService.dep()]
