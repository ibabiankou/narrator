from contextlib import asynccontextmanager

from pydantic import BaseModel

from api.kokoro import KokoroService
from fastapi import FastAPI, APIRouter, Response
from kokoro import KPipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    KokoroService.initialize()
    yield


app = FastAPI(lifespan=lifespan)

base_url_router = APIRouter(prefix="/api")


@base_url_router.get("/")
def health():
    return {"status": "ok"}


pipeline = KPipeline(lang_code='a')


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
