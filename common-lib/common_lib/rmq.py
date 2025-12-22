import copy
import logging
import os
import random
from dataclasses import dataclass
from enum import StrEnum
from threading import Thread, RLock, Event
from typing import Optional, ClassVar, Callable, TypeVar, Any, Type

from pika import BlockingConnection, ConnectionParameters, BasicProperties, PlainCredentials
from pika.exceptions import ConnectionWrongStateError
from pika.spec import Basic
from pika.adapters.blocking_connection import BlockingChannel
from pydantic import BaseModel
from tenacity import retry, wait_exponential, wait_random, stop_after_attempt, RetryError

from common_lib.service import Service

LOG = logging.getLogger(__name__)


class RMQMessage(BaseModel):
    """A base class for all RMQ messages. Subclasses MUST set the type attribute, and it should be globally unique."""

    # Type of the message. Used by consumers to match the message to an appropriate handler.
    type: ClassVar[str]


SubclassOfRMQMessage: TypeVar = TypeVar("SubclassOfRMQMessage", bound=RMQMessage)

default_connection_params = ConnectionParameters(
    host=os.getenv("RMQ_HOST"),
    port=int(os.getenv("RMQ_PORT")),
    credentials=PlainCredentials(os.getenv("RMQ_USERNAME"), os.getenv("RMQ_PASSWORD")),
    client_properties={"connection_name": os.getenv("HOSTNAME", "narrator-api")},
    heartbeat=20
)


class RMQClient(Service):
    def __init__(self, exchange: str, queue: str):
        self.exchange = exchange
        self.queue = queue

        self._publisher_connection = WatchedConnectionProvider(default_connection_params, ConnectionPurpose.PUBLISHER)
        self._consumer_connection = WatchedConnectionProvider(default_connection_params, ConnectionPurpose.CONSUMER)

        self._consumer_watchdog_thread = Thread(target=self._consume, daemon=True)
        self._message_handlers: dict[str, MsgHandlerContext] = {}

        self._close = Event()

    def configure(self, configure_callback: Callable[[BlockingChannel], Any]):
        LOG.info("Configuring topology...")
        channel = self._publisher_connection.get().channel()
        configure_callback(channel)
        channel.close()

    def set_consumer(self, cls: type[SubclassOfRMQMessage], message_handler: Callable[[SubclassOfRMQMessage], Any]):
        self._message_handlers[cls.type] = MsgHandlerContext(msg_type=cls, handler=message_handler)

    def start_consuming(self):
        self._consumer_watchdog_thread.start()

    def _consume(self):
        def _invoke_handler(invocation: MsgHandlerInvocation):
            conn: BlockingConnection = invocation.channel.connection
            try:
                invocation.context.handler(invocation.payload)
                conn.add_callback_threadsafe(
                    lambda: invocation.channel.basic_ack(delivery_tag=invocation.delivery_tag)
                )
            except Exception:
                LOG.exception(f"Error while handling message of type {invocation.payload.type}. Ignoring it...")
                conn.add_callback_threadsafe(
                    lambda: invocation.channel.basic_reject(delivery_tag=invocation.delivery_tag)
                )

        def _message_handler(channel: BlockingChannel, method: Basic.Deliver, properties: BasicProperties, body: bytes):
            msg_type = properties.type
            LOG.debug("Handling message of type %s...", msg_type)

            if msg_type in self._message_handlers:
                ctx = self._message_handlers[msg_type]
                payload = ctx.msg_type.model_validate_json(body)
                handler_invocation = MsgHandlerInvocation(context=ctx, payload=payload, channel=channel,
                                                          delivery_tag=method.delivery_tag)

                # TODO: replace with long lived thread and a queue of handler_invocations.
                t = Thread(name=f"msg-{method.delivery_tag}", target=_invoke_handler, args=[handler_invocation],
                           daemon=True)
                t.start()

                while t.is_alive():
                    t.join(1)
                    channel.connection.process_data_events()
            else:
                LOG.info(f"Received message of type {msg_type}, but no handler is registered. Rejecting it...")
                channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

        while not self._close.is_set():
            try:
                ch = self._consumer_connection.get().channel()
                ch.basic_qos(prefetch_count=1)
                ch.basic_consume(queue=self.queue, on_message_callback=_message_handler)
                ch.start_consuming()
            except Exception:
                LOG.exception("Error while consuming from RMQ.")
                self._close.wait(1 + random.random())

    def publish(self, routing_key: str, payload: RMQMessage, properties: BasicProperties = None):
        channel = self._publisher_connection.default_channel()
        body = payload.model_dump_json().encode("utf-8")
        props = properties or BasicProperties()
        props.type = payload.type
        channel.basic_publish(self.exchange, routing_key, body, props, mandatory=True)

    def close(self):
        LOG.info("Closing RMQ client...")
        self._close.set()
        self._publisher_connection.close()
        self._consumer_connection.close()


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
            except RetryError:
                LOG.exception("Failed to get connection. Will keep trying.")

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

    def close(self):
        self._close.set()
        with self._lock:
            if self._connection and self._connection.is_open:
                self._connection.close()
