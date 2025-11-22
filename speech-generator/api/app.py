from fastapi import FastAPI, APIRouter
from kokoro import KPipeline
import soundfile as sf

app = FastAPI()

base_url_router = APIRouter(prefix="/api")


@base_url_router.get("/")
def health():
    return {"status": "ok"}


pipeline = KPipeline(lang_code='a')

@base_url_router.get("/test")
def test():
    text = "Lets test this thing out..."

    generator = pipeline(text, voice='af_heart')
    for i, (gs, ps, audio) in enumerate(generator):
        print(i, gs, ps)
        sf.write(f'{i}.wav', audio, 24000)

    return {"status": "ok"}


app.include_router(base_url_router)
