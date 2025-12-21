from contextlib import asynccontextmanager

from dotenv import load_dotenv
from pika.adapters.blocking_connection import BlockingChannel
from pika.exchange_type import ExchangeType
from pydantic import BaseModel

from api.speechgen import SpeechGenService, SpeechGenServiceDep
from fastapi import FastAPI, APIRouter, Response

from common_lib import RMQClient
from common_lib.models import rmq

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    exchange = "narrator"
    queue = "speech-generator"
    rmq_client: RMQClient = RMQClient(exchange, queue)
    speech_gen_svc = SpeechGenService(rmq_client)

    # Configure topology.
    def configure(channel: BlockingChannel):
        channel.exchange_declare(exchange, ExchangeType.topic, durable=True)
        channel.queue_declare(queue, durable=True, arguments={"x-queue-type": "quorum"})
        channel.queue_bind(queue, exchange, "phonemize")
        channel.queue_bind(queue, exchange, "synthesize")
    rmq_client.configure(configure)

    # Configure message handlers and start consuming.
    rmq_client.set_consumer(rmq.PhonemizeText, speech_gen_svc.handle_phonemize_msg)
    rmq_client.set_consumer(rmq.SynthesizeSpeech, speech_gen_svc.handle_synthesize_msg)
    rmq_client.start_consuming()
    yield


app = FastAPI(lifespan=lifespan)

base_url_router = APIRouter(prefix="/api")


@base_url_router.get("/")
def health():
    return {"status": "ok"}


class PhonemizeRequest(BaseModel):
    text: str


@base_url_router.post("/phonemize")
def phonemize(request: PhonemizeRequest, speech_gen_svc: SpeechGenServiceDep):
    phonemes = speech_gen_svc.phonemize(request.text)
    return {"phonemes": phonemes}


class SynthesizeRequest(BaseModel):
    phonemes: str


@base_url_router.post("/synthesize")
def synthesize(request: SynthesizeRequest, speech_gen_svc: SpeechGenServiceDep):
    result = speech_gen_svc.synthesize(request.phonemes)
    return Response(content=result.get("content"),
                    media_type=result.get("content_type"),
                    headers={"narrator-speech-duration": str(result.get("duration"))})


app.include_router(base_url_router)
