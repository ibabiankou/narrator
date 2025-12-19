from contextlib import asynccontextmanager

from dotenv import load_dotenv
from pika import BasicProperties
from pydantic import BaseModel

from api.kokoro import KokoroService
from fastapi import FastAPI, APIRouter, Response

from api.models.rmq import PhonemizeText, PhonemesResponse
from api.rmq import RMQClient

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    kokoro_service = KokoroService.create()

    rmq_client: RMQClient = RMQClient.create()

    def phonemize(payload: PhonemizeText, prop: BasicProperties):
        phonemes = kokoro_service.phonemize(payload.text)
        payload = PhonemesResponse(section_id=payload.section_id, phonemes=phonemes)
        rmq_client.publish(routing_key="phonemes", payload=payload)

    rmq_client.set_consumer("phonemize", PhonemizeText, phonemize)
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
