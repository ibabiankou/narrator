from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pika.adapters.blocking_connection import BlockingChannel
from pika.exchange_type import ExchangeType
from starlette.middleware.gzip import GZipMiddleware

from api.books import books_router
from api.files import files_router
from api.playlist import playlists_router
from api.sections import sections_router
from api.services.audiotracks import AudioTrackService
from api.services.books import BookService
from api.services.files import FilesService
from api.services.progress import PlaybackProgressService
from api.services.sections import SectionService
from common_lib import RMQClient
from common_lib.models import rmq

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()

    # Initialize services.
    files_svc = FilesService()
    books_svc = BookService(files_svc)
    playback_svc = PlaybackProgressService()

    exchange = "narrator"
    queue = "api"
    rmq_client = RMQClient(exchange, queue)
    audiotrack_svc = AudioTrackService(files_svc, rmq_client)
    section_svc = SectionService(audiotrack_svc)

    def configure(channel: BlockingChannel):
        channel.exchange_declare(exchange, ExchangeType.topic, durable=True)
        channel.queue_declare(queue, durable=True, arguments={"x-queue-type": "quorum"})
        channel.queue_bind(queue, exchange, "phonemes")
        channel.queue_bind(queue, exchange, "speech")
    rmq_client.configure(configure)

    rmq_client.set_consumer(rmq.PhonemesResponse, section_svc.handle_phonemes_msg)
    rmq_client.set_consumer(rmq.SpeechResponse, audiotrack_svc.handle_speech_msg)
    rmq_client.start_consuming()
    yield
    RMQClient.instance.close()

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


base_url_router.include_router(files_router, prefix="/files")
base_url_router.include_router(books_router, prefix="/books")
base_url_router.include_router(playlists_router, prefix="/playlists")
base_url_router.include_router(sections_router, prefix="/sections")
app.include_router(base_url_router)
