import logging
from contextlib import asynccontextmanager
from http.client import HTTPConnection

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from api.audio import audio_router
from api.books import books_router
from api.files import files_router
from api.playlist import playlists_router
from api.sections import sections_router
from api.services.audiotracks import SpeechGenerationQueue


# logging.basicConfig()
# logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)
#
# # Debug requests library
# HTTPConnection.debuglevel = 1
# logging.getLogger("requests.packages.urllib3").setLevel(logging.DEBUG)
# logging.getLogger("requests.packages.urllib3").propagate = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    SpeechGenerationQueue.singleton = SpeechGenerationQueue()
    yield

app = FastAPI(lifespan=lifespan)
origins = [
    "http://localhost",
    "http://localhost:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware)

base_url_router = APIRouter(prefix="/api")

@base_url_router.get("/")
def health():
    return {"status": "ok"}


base_url_router.include_router(audio_router, prefix="/audio")
base_url_router.include_router(files_router, prefix="/files")
base_url_router.include_router(books_router, prefix="/books")
base_url_router.include_router(playlists_router, prefix="/playlists")
base_url_router.include_router(sections_router, prefix="/sections")
app.include_router(base_url_router)
