from collections import deque
from dataclasses import dataclass
from logging import DEBUG

import av
import boto3
import io
import numpy as np
import os
from botocore.exceptions import ClientError
from datetime import datetime, UTC
from io import BytesIO
from kokoro import KModel, KPipeline
from misaki.token import MToken
from typing import Annotated, Tuple, List

from api import get_logger
from common_lib import RMQClientDep
from common_lib.models import rmq
from common_lib.models.tts import FragmentGroups, TextFragment, PauseFragment, FragmentDuration, \
    TrackManifest
from common_lib.service import Service

LOG = get_logger(__name__)

@dataclass
class TokenizedFragment:
    fragment: TextFragment
    tokens: List[MToken]


class SpeechGenService(Service):
    def __init__(self, rmq_client: RMQClientDep, lang_code: str = "a"):
        self.rmq_client = rmq_client
        self.model = KModel()
        self.speech_pipeline = KPipeline(lang_code, model=self.model, repo_id="hexgrad/Kokoro-82M")

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

    def handle_narrate_msg(self, payload: rmq.NarrateRequest):
        start_time = datetime.now(UTC)
        LOG.debug("Processing narration request %s.", payload.queue_id)
        base_key = f"{payload.book_id}/audio-files/{payload.tts_model}/{payload.voice}/{payload.track_base_name}"

        audio_key = f"{base_key}.aac"

        audio_np, timeline = self._narrate_track(payload.fragments, payload.voice)
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

    def _narrate_track(self, fragment_groups: FragmentGroups, voice: str) -> Tuple[
        np.ndarray, List[FragmentDuration]]:

        audio_np = None
        timings: List[FragmentDuration] = []

        batch = []
        for frag in fragment_groups.flatten():
            if isinstance(frag, TextFragment):
                batch.append(frag)
            elif isinstance(frag, PauseFragment):
                if len(batch) > 0:
                    batch_audio_np, batch_timings = self._narrate_fragments(batch, voice)
                    audio_np = batch_audio_np if audio_np is None else np.concatenate((audio_np, batch_audio_np), axis=0)
                    timings.extend(batch_timings)

                # Add the pause
                pause = self._silence(frag.duration)
                audio_np = pause if audio_np is None else np.concatenate((audio_np, pause), axis=0)
                timings.append(FragmentDuration(id=frag.id, duration=frag.duration))

                # Restart the batch
                batch = []

        if len(batch) > 0:
            # narrate the batch
            batch_audio_np, batch_timings = self._narrate_fragments(batch, voice)
            audio_np = batch_audio_np if audio_np is None else np.concatenate((audio_np, batch_audio_np), axis=0)
            timings.extend(batch_timings)

        # noinspection PyTypeChecker
        return audio_np, timings

    def _silence(self, duration_s: float):
        return np.zeros(int(duration_s * self.sample_rate), dtype=np.int16)

    def _narrate_fragments(self, fragments: List[TextFragment], voice: str) -> Tuple[np.ndarray, List[FragmentDuration]]:
        audio_np = None
        tokenized_fragments: List[TokenizedFragment] = []

        all_tokens = []
        for fragment in fragments:
            _, tokens = self.speech_pipeline.g2p(fragment.text)
            if not tokens:
                LOG.warning("No tokens generated for fragment '%s'.", fragment)
            all_tokens.extend(tokens)
            tokenized_fragments.append(
                TokenizedFragment(
                    fragment=fragment,
                    tokens=tokens
                )
            )

        results: List[KPipeline.Result] = []
        tokens_processed = 0
        for result in self.speech_pipeline.generate_from_tokens(all_tokens, voice):
            if result.tokens is None:
                raise RuntimeError(f"No tokens available in the result.")

            results.append(result)

            tokens_processed += len(result.tokens)
            LOG.info("Batch progress: %.1f%%", tokens_processed/len(all_tokens)*100)
            # if LOG.isEnabledFor(DEBUG):
            #     LOG.debug(result.graphemes)
            #     for t in result.tokens:
            #         LOG.debug(t)

            self._fix_token_times(result)

            result_audio_np = result.audio.numpy()
            result_duration_s = result_audio_np.size / self.sample_rate
            LOG.debug("Batch duration seconds: %s", result_duration_s)

            audio_np = result_audio_np if audio_np is None else np.concatenate((audio_np, result_audio_np), axis=0)

        if audio_np is None:
            raise RuntimeError("Audio is empty.")

        duration_s = audio_np.size / self.sample_rate
        LOG.debug("Total duration seconds: %s", duration_s)

        return audio_np, self._calculate_timeline(tokenized_fragments, results)

    def _fix_token_times(self, result: KPipeline.Result):
        if result.tokens is None:
            return

        # The first token does not include fade-in duration.
        result.tokens[0].start_ts = 0

        if result.audio is None or len(result.tokens) < 2:
            return

        # The last token does not include fade-out duration.
        last = result.tokens[-1]
        result_duration = result.audio.numpy().size / self.sample_rate
        last.end_ts = result_duration

        # Ensure start_ts of the last token is there.
        second_to_last = result.tokens[-2]
        if last.start_ts is None:
            last.start_ts = second_to_last.end_ts

        # When a token does not have corresponding phonemes, its start/end time will be None. Set those to the last
        # seen time to maintain continuity.
        last_known_time = 0
        for t in result.tokens:
            if t.start_ts is None:
                t.start_ts = last_known_time
            else:
                last_known_time = t.start_ts
            if t.end_ts is None:
                t.end_ts = last_known_time
            else:
                last_known_time = t.end_ts


    def _calculate_timeline(self, fragments: List[TokenizedFragment], results: List[KPipeline.Result]) -> List[FragmentDuration]:
        # Fix the overall timeline continuity across all results.
        if len(results) > 1:
            for i in range(1, len(results)):
                previous_batch = results[i-1].tokens
                current_batch = results[i].tokens
                # noinspection PyTypeChecker
                for token in current_batch:
                    token.start_ts += previous_batch[-1].end_ts
                    token.end_ts += previous_batch[-1].end_ts

        all_tokens = deque[MToken]()
        for result in results:
            # noinspection PyTypeChecker
            all_tokens.extend(result.tokens)

        timeline = []
        for fragment in fragments:
            if not fragment.tokens:
                timeline.append(FragmentDuration(id=fragment.fragment.id, duration=0))
            else:
                start_time = fragment.tokens[0].start_ts or 0
                end_time = fragment.tokens[-1].end_ts or 0
                timeline.append(FragmentDuration(id=fragment.fragment.id, duration=end_time - start_time))
        return timeline

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
