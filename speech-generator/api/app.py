from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from pika.adapters.blocking_connection import BlockingChannel
from pika.exchange_type import ExchangeType

from api.speechgen import SpeechGenService
from common_lib import RMQClient
from common_lib.models import rmq
from common_lib.rmq import Topology
from common_lib.uvicorn import EndpointFilter

load_dotenv()
EndpointFilter.add_filter("/api/")

@asynccontextmanager
async def lifespan(app: FastAPI):
    exchange = "narrator"
    rmq_client: RMQClient = RMQClient(exchange)
    speech_gen_svc = SpeechGenService(rmq_client)

    # Configure topology.
    def configure(channel: BlockingChannel):
        channel.exchange_declare(exchange, ExchangeType.topic, durable=True)
        channel.queue_declare(Topology.narration_queue, durable=True, arguments={"x-queue-type": "quorum"})
        channel.queue_bind(Topology.narration_queue, exchange, "narrate")

    rmq_client.configure(configure)

    # Configure message handlers and start consuming.
    rmq_client.set_queue_message_handler(Topology.narration_queue,
                                         rmq.NarrateRequest,
                                         speech_gen_svc.handle_narrate_msg)
    rmq_client.start_consuming()
    yield


app = FastAPI(lifespan=lifespan)

base_url_router = APIRouter(prefix="/api")


@base_url_router.get("/")
def health():
    return {"status": "ok"}

app.include_router(base_url_router)
