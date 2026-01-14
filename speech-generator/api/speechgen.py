import mimetypes
import os
from dataclasses import dataclass
from io import BytesIO
from typing import Annotated

import boto3
from botocore.exceptions import ClientError
from kokoro import KModel, KPipeline
from soundfile import SoundFile

from api import get_logger
from common_lib import RMQClientDep
from common_lib.models import rmq
from common_lib.service import Service

LOG = get_logger(__name__)

@dataclass
class GeneratedSpeech:
    content: bytes
    content_type: str
    duration: float


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
        phonemes = self.phonemize(payload.text, payload.voice)
        payload = rmq.PhonemesResponse(book_id=payload.book_id, section_id=payload.section_id,
                                       track_id=payload.track_id, phonemes=phonemes, voice=payload.voice)
        self.rmq_client.publish(routing_key="phonemes", payload=payload)

    def synthesize(self, phonemes: str, voice: str = "am_adam", speed: float = 1) -> GeneratedSpeech:
        audio_buf = BytesIO()
        audio_format = os.getenv("AUDIO_FORMAT", "mp3")
        audio_subtype = os.getenv("AUDIO_SUBTYPE", "MPEG_LAYER_III")
        content_type = os.getenv("AUDIO_CONTENT_TYPE", "audio/mpeg")
        with SoundFile(audio_buf, mode="w",
                       format=audio_format, subtype=audio_subtype,
                       samplerate=24000, channels=1,
                       compression_level=0.5) as sf:
            chunks = phonemes.split("\n")
            for chunk in chunks:
                if not chunk.strip():
                    continue
                for result in self.speech_pipeline.generate_from_tokens(tokens=chunk, voice=voice, speed=speed):
                    sf.write(result.audio)

        audio_buf.seek(0)
        return GeneratedSpeech(content=audio_buf.read(), content_type=content_type, duration=sf.frames / sf.samplerate)

    def handle_synthesize_msg(self, payload: rmq.SynthesizeSpeech):
        LOG.debug("Synthesizing speech for track %s.", payload.track_id)
        result = self.synthesize(payload.phonemes, payload.voice, payload.speed)

        file_ext = mimetypes.guess_extension(result.content_type)
        if file_ext is None:
            raise ValueError(f"Unable to guess file extension based on content type: {result.content_type}")
        key = f"{payload.file_path}/{payload.track_id}{file_ext}"
        self._upload_file(key, result.content_type, result.content)
        payload = rmq.SpeechResponse(book_id=payload.book_id, section_id=payload.section_id, track_id=payload.track_id,
                                     file_path=key, duration=result.duration, bytes=len(result.content))
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

    def _list_files(self, path_prefix: str):
        paginator = self.s3_client.get_paginator('list_objects_v2')

        keys = []
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=path_prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    keys.append(obj["Key"])

        return keys

    def _load_file(self, key: str) -> bytes:
        s3_object = self.s3_client.get_object(Bucket=self.bucket_name,
                                              Key=key)
        return s3_object["Body"].read()

SpeechGenServiceDep = Annotated[SpeechGenService, SpeechGenService.dep()]
