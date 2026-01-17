from contextlib import asynccontextmanager

from dotenv import load_dotenv
from pika.adapters.blocking_connection import BlockingChannel
from pika.exchange_type import ExchangeType
from pydantic import BaseModel

from api.speechgen import SpeechGenService, SpeechGenServiceDep
from fastapi import FastAPI, APIRouter, Response

from common_lib import RMQClient
from common_lib.models import rmq
from common_lib.rmq import Topology

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    exchange = "narrator"
    rmq_client: RMQClient = RMQClient(exchange)
    speech_gen_svc = SpeechGenService(rmq_client)

    # Configure topology.
    def configure(channel: BlockingChannel):
        channel.exchange_declare(exchange, ExchangeType.topic, durable=True)
        channel.queue_declare(Topology.phonemization_queue, durable=True,
                              arguments={"x-queue-type": "quorum"})
        channel.queue_bind(Topology.phonemization_queue, exchange, "phonemize")
        channel.queue_declare(Topology.speech_gen_queue, durable=True, arguments={"x-queue-type": "quorum"})
        channel.queue_bind(Topology.speech_gen_queue, exchange, "synthesize")

    rmq_client.configure(configure)

    # Configure message handlers and start consuming.
    rmq_client.set_queue_message_handler(Topology.phonemization_queue,
                                         rmq.PhonemizeText,
                                         speech_gen_svc.handle_phonemize_msg)
    rmq_client.set_queue_message_handler(Topology.speech_gen_queue,
                                         rmq.SynthesizeSpeech,
                                         speech_gen_svc.handle_synthesize_msg)
    rmq_client.start_consuming()
    yield


app = FastAPI(lifespan=lifespan)

base_url_router = APIRouter(prefix="/api")


@base_url_router.get("/")
def health():
    return {"status": "ok"}


class PhonemizeRequest(BaseModel):
    text: str
    voice: str


@base_url_router.post("/phonemize")
def phonemize(request: PhonemizeRequest, speech_gen_svc: SpeechGenServiceDep):
    phonemes = speech_gen_svc.phonemize(request.text, request.voice)
    return {"phonemes": phonemes}


class SynthesizeRequest(BaseModel):
    phonemes: str
    voice: str
    speed: float


@base_url_router.post("/synthesize")
def synthesize(request: SynthesizeRequest, speech_gen_svc: SpeechGenServiceDep):
    result = speech_gen_svc.synthesize(request.phonemes, request.voice)
    return Response(content=result.content,
                    media_type=result.content_type,
                    headers={"narrator-speech-duration": str(result.duration)})


app.include_router(base_url_router)
