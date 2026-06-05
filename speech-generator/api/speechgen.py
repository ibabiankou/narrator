import av
import boto3
import io
import numpy as np
import os
from botocore.exceptions import ClientError
from dataclasses import dataclass
from datetime import datetime, UTC
from io import BytesIO
from kokoro import KModel, KPipeline
from typing import Annotated, Tuple, Optional, List

from api import get_logger
from common_lib import RMQClientDep
from common_lib.models import rmq
from common_lib.models.tts import FragmentList, Fragment, TextFragment, PauseFragment, FragmentDuration, \
    TrackManifest
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
        # Kokoro generates audio at 24kHz
        self.sample_rate = 24000

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

    def synthesize(self, phonemes: str, voice: str = "am_adam") -> GeneratedSpeech:
        audio_np = None

        chunks = phonemes.split("\n")
        for chunk in chunks:
            if not chunk.strip():
                continue
            for result in self.speech_pipeline.generate_from_tokens(tokens=chunk, voice=voice):
                if audio_np is None:
                    audio_np = result.audio.numpy()
                else:
                    audio_np = np.concatenate((audio_np, result.audio.numpy()), axis=0)

        output, duration_s = self._encode_audio(audio_np)

        return GeneratedSpeech(content=output.getvalue(), content_type="audio/aac",
                               duration=duration_s)

    def handle_synthesize_msg(self, payload: rmq.SynthesizeSpeech):
        LOG.debug("Synthesizing speech for track %s.", payload.track_id)
        result = self.synthesize(payload.phonemes, payload.voice)

        key = f"{payload.file_path}/{payload.track_id}.aac"
        self._upload_file(key, result.content_type, result.content)
        payload = rmq.SpeechResponse(book_id=payload.book_id, section_id=payload.section_id, track_id=payload.track_id,
                                     file_path=key, duration=result.duration, bytes=len(result.content))
        self.rmq_client.publish(routing_key="speech", payload=payload)

    def handle_narrate_msg(self, payload: rmq.NarrateRequest):
        start_time = datetime.now(UTC)
        LOG.debug("Processing narration request %s.", payload.queue_id)
        base_key = f"{payload.book_id}/audio-files/{payload.tts_model}/{payload.voice}/{payload.track_base_name}"

        audio_key = f"{base_key}.aac"

        audio_np, timeline = self._narrate_fragments(payload.fragments, payload.voice)
        audio_bytes, duration_s = self._encode_audio(audio_np)
        self._upload_file(audio_key, "audio/aac", audio_bytes.getvalue())

        track_manifest_key = f"{base_key}.json"
        manifest = TrackManifest(
            audio_key=audio_key,
            size_bytes=len(audio_bytes.getvalue()),
            track_name=payload.track_base_name,
            timeline=timeline,
        )
        self._upload_file(track_manifest_key, "application/json", manifest.model_dump_json().encode())

        end_time = datetime.now(UTC)
        narration_time_s = (end_time - start_time).total_seconds()
        response_payload = rmq.NarrateResponse(
            queue_id=payload.queue_id,
            completed=datetime.now(UTC),
            narration_time_s=narration_time_s,
            duration_s=duration_s,
            size_bytes=len(audio_bytes.getvalue())
        )
        self.rmq_client.publish(routing_key="narrate-response", payload=response_payload)

    def _encode_audio(self, audio_np: np.ndarray) -> Tuple[BytesIO, float]:
        output = io.BytesIO()
        with av.open(output, mode='w', format='adts') as container:
            stream = container.add_stream('aac', rate=self.sample_rate, bit_rate=64000)

            audio_np = audio_np.astype(np.float32).reshape(1, -1)

            frame = av.AudioFrame.from_ndarray(audio_np, format='fltp', layout='mono')
            frame.sample_rate = self.sample_rate

            total_duration_pts = 0
            for packet in stream.encode(frame):
                container.mux(packet)
                if packet.duration:
                    total_duration_pts += packet.duration
            for packet in stream.encode():
                container.mux(packet)
                if packet.duration:
                    total_duration_pts += packet.duration

        return output, float(total_duration_pts * stream.time_base)

    def _narrate_fragments(self, fragments: FragmentList, voice: str) -> Tuple[np.ndarray, List[FragmentDuration]]:
        audio_np = None
        timings: List[FragmentDuration] = []
        for fragment in fragments.root:
            frag: Fragment = fragment
            if isinstance(frag, TextFragment):
                result_maybe = self._narrate_fragment(frag, voice)
                if result_maybe is None:
                    raise RuntimeError("Failed to narrate fragment: %s", frag.id)
                frag_audio, fragment_duration_s = result_maybe
                audio_np = frag_audio if audio_np is None else np.concatenate((audio_np, frag_audio), axis=0)
                timings.append(FragmentDuration(id=frag.id, duration=fragment_duration_s))
            elif isinstance(frag, PauseFragment):
                pause = self._silence(frag.duration)
                audio_np = pause if audio_np is None else np.concatenate((audio_np, pause), axis=0)
                timings.append(FragmentDuration(id=frag.id, duration=frag.duration))

        # noinspection PyTypeChecker
        return audio_np, timings

    def _silence(self, duration_s: float):
        return np.zeros(int(duration_s * self.sample_rate), dtype=np.int16)

    def _narrate_fragment(self, frag: TextFragment, voice: str) -> Optional[Tuple[np.ndarray, float]]:
        audio_np = None

        for result in self.speech_pipeline(frag.text, voice):
            LOG.debug("Graphemes: %s", result.graphemes)
            if audio_np is None:
                audio_np = result.audio.numpy()
            else:
                audio_np = np.concatenate((audio_np, result.audio.numpy()), axis=0)

        if audio_np is None:
            return None

        duration_s = audio_np.size / self.sample_rate
        LOG.debug("Total duration seconds: %s", duration_s)

        return audio_np, duration_s

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
