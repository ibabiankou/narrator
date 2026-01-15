import io
import mimetypes
import os
from dataclasses import dataclass
from io import BytesIO
from typing import Annotated

import av
import boto3
import numpy as np
from botocore.exceptions import ClientError
from kokoro import KModel, KPipeline
from soundfile import SoundFile
from sympy.stats import sample_iter

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
        audio_np = None
        sample_rate = 24000

        chunks = phonemes.split("\n")
        for chunk in chunks:
            if not chunk.strip():
                continue
            for result in self.speech_pipeline.generate_from_tokens(tokens=chunk, voice=voice, speed=speed):
                if audio_np is None:
                    audio_np = result.audio.numpy()
                else:
                    audio_np = np.concatenate((audio_np, result.audio.numpy()), axis=0)

        n_samples = audio_np.shape[-1]
        duration = n_samples / sample_rate

        options = {
            'movflags': 'frag_keyframe+empty_moov+default_base_moof',
            'flush_packets': '1'
        }

        output = io.BytesIO()
        with av.open(output, mode='w', format='mp4', options=options) as container:
            stream = container.add_stream('opus', rate=sample_rate, bit_rate=32000)

            # 2. Prepare Kokoro Audio
            # Ensure it is float32 and reshaped for mono
            audio_np = audio_np.astype(np.float32).reshape(1, -1)

            # 3. Create AV Frame
            frame = av.AudioFrame.from_ndarray(audio_np, format='fltp', layout='mono')
            frame.sample_rate = sample_rate

            # 4. Encode and Mux
            for packet in stream.encode(frame):
                container.mux(packet)

            # 5. Flush Encoder
            for packet in stream.encode():
                container.mux(packet)

        return GeneratedSpeech(content=output.getvalue(), content_type="video/iso.segment", duration=duration)

    def handle_synthesize_msg(self, payload: rmq.SynthesizeSpeech):
        LOG.debug("Synthesizing speech for track %s.", payload.track_id)
        result = self.synthesize(payload.phonemes, payload.voice, payload.speed)

        key = f"{payload.file_path}/{payload.track_id}.m4s"
        self._upload_file(key, result.content_type, result.content)
        payload = rmq.SpeechResponse(book_id=payload.book_id, section_id=payload.section_id, track_id=payload.track_id,
                                     file_path=key, duration=result.duration, bytes=len(result.content))
        self.rmq_client.publish(routing_key="speech", payload=payload)

    def handle_generate_media_header_msg(self, payload: rmq.GenerateMediaHeader):
        # Pass muxer options directly during container opening
        options = {
            'movflags': 'frag_keyframe+empty_moov+default_base_moof',
        }
        sample_rate = 24000

        output = io.BytesIO()
        with av.open(output, mode='w', format='mp4', options=options) as container:
            stream = container.add_stream('opus', rate=sample_rate)
            # We don't mux any packets. Closing the container now
            # writes only the metadata (ftyp + moov).

        key = f"{payload.book_id}/map.mp4"
        self._upload_file(key, "audio/mp4", output.getvalue())


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
