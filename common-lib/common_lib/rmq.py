import copy
import logging
import os
import random
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from queue import Queue, Empty
from threading import Thread, RLock, Event
from typing import Optional, ClassVar, Callable, TypeVar, Any, Type

from pika import BlockingConnection, ConnectionParameters, BasicProperties, PlainCredentials
from pika.exceptions import ConnectionWrongStateError
from pika.exchange_type import ExchangeType
from pika.spec import Basic
from pika.adapters.blocking_connection import BlockingChannel
from pydantic import BaseModel
from tenacity import retry, wait_exponential, wait_random, stop_after_attempt

from common_lib.service import Service

LOG = logging.getLogger(__name__)


class RMQMessage(BaseModel):
    """A base class for all RMQ messages. Subclasses MUST set the type attribute, and it should be globally unique."""

    # Type of the message. Used by consumers to match the message to an appropriate handler.
    type: ClassVar[str]


SubclassOfRMQMessage: TypeVar = TypeVar("SubclassOfRMQMessage", bound=RMQMessage)

default_connection_params = ConnectionParameters(
    host=os.getenv("RMQ_HOST", "undefined"),
    port=int(os.getenv("RMQ_PORT", 5672)),
    credentials=PlainCredentials(os.getenv("RMQ_USERNAME"), os.getenv("RMQ_PASSWORD")),
    client_properties={"connection_name": os.getenv("HOSTNAME", "narrator-api")},
    heartbeat=20
)

class Topology:
    default_exchange = "narrator"
    api_queue = "api"
    phonemization_queue = "phonemization"
    speech_gen_queue = "speech-generation"


class RMQClient(Service):
    def __init__(self, exchange: str):
        self.exchange = exchange

        self._publisher_connection = WatchedConnectionProvider(default_connection_params, ConnectionPurpose.PUBLISHER)
        self._consumer_connection = WatchedConnectionProvider(default_connection_params, ConnectionPurpose.CONSUMER)

        self._consumer_thread = Thread(name="rmq-consumer", target=self._consume, daemon=True)
        self._message_handler_registry: QueueMessageHandlerRegistry = defaultdict(dict)
        self._message_processor = MessageProcessor(int(os.getenv("RMQ_CONCURRENCY", 1)))

        self._close = Event()

    def configure(self, configure_callback: Callable[[BlockingChannel], Any]):
        LOG.info("Configuring topology...")
        channel = self._publisher_connection.channel()
        configure_callback(channel)
        channel.close()

    def get_queue_size(self, queue_name: str):
        channel = self._publisher_connection.default_channel()
        return channel.queue_declare(queue_name, passive=True).method.message_count

    def set_queue_message_handler(self, queue: str, cls: type[SubclassOfRMQMessage],
                                  message_handler: Callable[[SubclassOfRMQMessage], Any]):
        self._message_handler_registry[queue][cls.type] = MsgHandlerContext(msg_type=cls, handler=message_handler)

    def start_consuming(self):
        LOG.info("Starting RMQ consumer thread")
        LOG.debug("Message handler registry: \n%s", self._message_handler_registry)
        self._consumer_thread.start()

    def _consume(self):
        while not self._close.is_set():
            channel_name = "unknown"
            try:
                ch = self._consumer_connection.channel()
                ch.basic_qos(prefetch_count=1)
                connection_name = ch.connection._impl.params.client_properties.get('connection_name')
                channel_name = f"{connection_name} ({ch.channel_number})"

                for queue in self._message_handler_registry.keys():
                    LOG.info("Consuming queue '%s' on '%s'...", queue, channel_name)
                    wrapped_callback = partial(self._message_handler, queue)
                    ch.basic_consume(queue=queue, on_message_callback=wrapped_callback)
                ch.start_consuming()
            except Exception:
                LOG.exception("Error while consuming '%s'.", channel_name)
                self._close.wait(1 + random.random())

    def _message_handler(self, queue: str, channel: BlockingChannel, method: Basic.Deliver, properties: BasicProperties,
                         body: bytes):
        msg_type = properties.type
        LOG.debug("Handling message of type '%s' from queue '%s'...", msg_type, queue)

        message_handlers = self._message_handler_registry[queue]
        if msg_type in message_handlers:
            ctx = message_handlers[msg_type]
            payload = ctx.msg_type.model_validate_json(body)
            self._message_processor.put(MsgHandlerInvocation(context=ctx, payload=payload, channel=channel,
                                                             delivery_tag=method.delivery_tag))
        else:
            LOG.warning("Received message of type '%s' from queue '%s', but no handler is registered. Dropping it...",
                        msg_type, queue)
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

    def publish(self, routing_key: str, payload: RMQMessage, properties: BasicProperties = None):
        channel = self._publisher_connection.default_channel()
        body = payload.model_dump_json().encode("utf-8")
        props = properties or BasicProperties()
        props.type = payload.type
        channel.connection.add_callback_threadsafe(
            lambda: channel.basic_publish(self.exchange, routing_key, body, props, mandatory=True)
        )

    def close(self):
        LOG.info("Closing RMQ client...")
        self._close.set()
        self._publisher_connection.close()
        self._consumer_connection.close()
        self._message_processor.close()


@dataclass
class MsgHandlerContext[SubclassOfRMQMessage]:
    msg_type: Type[SubclassOfRMQMessage]
    handler: Callable[[SubclassOfRMQMessage], Any]


@dataclass
class MsgHandlerInvocation:
    context: MsgHandlerContext[Any]
    payload: RMQMessage
    channel: BlockingChannel
    delivery_tag: int


MessageHandlers = dict[str, MsgHandlerContext]
QueueMessageHandlerRegistry = defaultdict[str, MessageHandlers]


class MessageProcessor:
    """A single threaded message processor. All enqueued messages are handled in FIFO order."""

    def __init__(self, concurrency: int):
        self._close = Event()

        self.invocation_queue: Queue[MsgHandlerInvocation] = Queue()
        self.threads = []
        for i in range(concurrency):
            self.thread = Thread(name=f"message-processor-{i}", target=self._process_queue, daemon=True)
            self.threads.append(self.thread)
            self.thread.start()

    def put(self, invocation: MsgHandlerInvocation):
        # Limit timeout to fail fast. Should never happen because the queue is unbounded.
        self.invocation_queue.put(invocation, timeout=1)

    def _process_queue(self):
        while not self._close.is_set():
            try:
                self._handle_invocation(self.invocation_queue.get(timeout=0.1))
            except Empty:
                # Do nothing and continue to the next iteration
                pass

    @staticmethod
    def _handle_invocation(invocation: MsgHandlerInvocation):
        conn: BlockingConnection = invocation.channel.connection
        try:
            if invocation.channel.is_open:
                invocation.context.handler(invocation.payload)
                conn.add_callback_threadsafe(
                    lambda: invocation.channel.basic_ack(delivery_tag=invocation.delivery_tag)
                )
            else:
                LOG.warning(f"Channel is closed before handling message of type {invocation.payload.type}.")
        except Exception:
            LOG.exception(f"Error while handling message of type {invocation.payload.type}. Ignoring it...")
            conn.add_callback_threadsafe(
                lambda: invocation.channel.basic_reject(delivery_tag=invocation.delivery_tag)
            )

    def close(self):
        self._close.set()


class ConnectionPurpose(StrEnum):
    PUBLISHER = "publisher"
    CONSUMER = "consumer"


class WatchedConnectionProvider:
    """A provider that maintains RMQ connection open."""

    def __init__(self, connection_params: ConnectionParameters, connection_purpose: ConnectionPurpose):
        self.connection_params = copy.deepcopy(connection_params)
        self.connection_params.client_properties["purpose"] = connection_purpose.value
        self.connection_purpose = connection_purpose

        self._connection: Optional[BlockingConnection] = None
        self._default_channel: Optional[BlockingChannel] = None

        self._lock = RLock()
        self._close = Event()

        self._watchdog_thread = Thread(target=self._watchdog, daemon=True)
        self._watchdog_thread.start()

    def _watchdog(self):
        # as long as not closed, keep checking if it's open.
        while not self._close.is_set():
            try:
                self._close.wait(3)
                if self._close.is_set():
                    LOG.info("Connection is closed, stopping watchdog thread.")
                    break
                conn = self.get()
                if self.connection_purpose == ConnectionPurpose.PUBLISHER:
                    # Consumer connection is processing data events internally as part of start_consuming
                    # Publisher connection, however, should manually trigger this processing.
                    conn.process_data_events()
            except Exception:
                LOG.exception("Error getting connection in watchdog thread. Will keep trying.")

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10) + wait_random(0, 1),
        stop=stop_after_attempt(8)
    )
    def get(self) -> BlockingConnection:
        if self._close.is_set():
            raise ConnectionWrongStateError("Connection is closed.")

        with self._lock:
            if not self._connection or not self._connection.is_open:
                self._connection = BlockingConnection(self.connection_params)

        return self._connection

    def default_channel(self):
        if self._close.is_set():
            raise ConnectionWrongStateError("Connection is closed.")

        with self._lock:
            if not self._default_channel or not self._default_channel.is_open:
                self._default_channel = self.get().channel()
                if self.connection_purpose == ConnectionPurpose.PUBLISHER:
                    self._default_channel.confirm_delivery()

        return self._default_channel

    def channel(self):
        with self._lock:
            return self.get().channel()

    def close(self):
        self._close.set()
        with self._lock:
            if self._connection and self._connection.is_open:
                self._connection.close()
