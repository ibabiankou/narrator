import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pika.adapters.blocking_connection import BlockingChannel
from pika.exchange_type import ExchangeType
from starlette.middleware.gzip import GZipMiddleware

from api.books import books_router
from api.debug import debug_router
from api.files import files_router
from api.sections import sections_router
from api.services.audiotracks import AudioTrackService
from api.services.books import BookService
from api.services.files import FilesService
from api.services.progress import PlaybackProgressService
from api.services.sections import SectionService
from common_lib import RMQClient
from common_lib.models import rmq
from common_lib.rmq import Topology
from common_lib.uvicorn import EndpointFilter

load_dotenv()
# Filter out health check from access logs.
EndpointFilter.add_filter("/api/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()

    # Initialize services.
    files_svc = FilesService()
    progress_svc = PlaybackProgressService()

    rmq_client = RMQClient(Topology.default_exchange)
    audiotrack_svc = AudioTrackService(files_svc, rmq_client)
    section_svc = SectionService(audiotrack_svc, progress_svc, rmq_client)
    speech_gen_task = asyncio.create_task(section_svc.generate_speech_maybe())
    books_svc = BookService(files_svc, section_svc, progress_svc)

    def configure(channel: BlockingChannel):
        channel.exchange_declare(Topology.default_exchange, ExchangeType.topic, durable=True)
        channel.queue_declare(Topology.api_queue, durable=True, arguments={"x-queue-type": "quorum"})
        channel.queue_bind(Topology.api_queue, Topology.default_exchange, "phonemes")
        channel.queue_bind(Topology.api_queue, Topology.default_exchange, "speech")

    rmq_client.configure(configure)

    rmq_client.set_queue_message_handler(Topology.api_queue, rmq.PhonemesResponse, section_svc.handle_phonemes_msg)
    rmq_client.set_queue_message_handler(Topology.api_queue, rmq.SpeechResponse, audiotrack_svc.handle_speech_msg)
    rmq_client.start_consuming()
    yield
    speech_gen_task.cancel()
    RMQClient.instance.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Etag", "Content-Range"],
)
app.add_middleware(GZipMiddleware)

base_url_router = APIRouter(prefix="/api")


@base_url_router.get("/", tags=["System API"])
def health_check():
    return {"status": "ok"}


base_url_router.include_router(files_router, prefix="/files")
base_url_router.include_router(books_router, prefix="/books")
base_url_router.include_router(sections_router, prefix="/sections")
base_url_router.include_router(debug_router, prefix="/debug")
app.include_router(base_url_router)
