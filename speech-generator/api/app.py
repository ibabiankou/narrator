from contextlib import asynccontextmanager

from dotenv import load_dotenv
from pika import BasicProperties
from pika.adapters.blocking_connection import BlockingChannel
from pika.exchange_type import ExchangeType
from pydantic import BaseModel

from api.kokoro import KokoroService
from fastapi import FastAPI, APIRouter, Response

from common_lib import RMQClient
from common_lib.models import rmq

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    kokoro_service = KokoroService.create()

    exchange = "narrator"
    queue = "speech-generator"
    rmq_client: RMQClient = RMQClient.create(exchange, queue)

    def configure(channel: BlockingChannel):
        channel.exchange_declare(exchange, ExchangeType.topic, durable=True)
        channel.queue_declare(queue, durable=True, arguments={"x-queue-type": "quorum"})
        channel.queue_bind(queue, exchange, "phonemize")
        channel.queue_bind(queue, exchange, "synthesize")
    rmq_client.configure(configure)

    def phonemize(payload: rmq.PhonemizeText, prop: BasicProperties):
        phonemes = kokoro_service.phonemize(payload.text)
        payload = rmq.PhonemesResponse(section_id=payload.section_id, phonemes=phonemes)
        rmq_client.publish(routing_key="phonemes", payload=payload)

    rmq_client.set_consumer("phonemize", rmq.PhonemizeText, phonemize)
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
def phonemize(request: PhonemizeRequest):
    phonemes = KokoroService.instance.phonemize(request.text)
    return {"phonemes": phonemes}


class SynthesizeRequest(BaseModel):
    phonemes: str


@base_url_router.post("/synthesize")
def synthesize(request: SynthesizeRequest):
    result = KokoroService.instance.synthesize(request.phonemes)
    return Response(content=result.get("content"),
                    media_type=result.get("content_type"),
                    headers={"narrator-speech-duration": str(result.get("duration"))})


app.include_router(base_url_router)
