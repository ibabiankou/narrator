import logging
import os
import random
import time
from threading import Thread, RLock
from typing import Optional, ClassVar

from pika import BlockingConnection, ConnectionParameters, BasicProperties, PlainCredentials
from pika.spec import Basic
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import ConnectionWrongStateError, ChannelError, AMQPChannelError
from pydantic import BaseModel

from common_lib.service import Service

LOG = logging.getLogger(__name__)


class RMQMessage(BaseModel):
    """A base class for all RMQ messages. Subclasses MUST set the type attribute, and it should be globally unique."""

    # Type of the message. Used by consumers to match the message to an appropriate handler.
    type: ClassVar[str]

class RMQClient(Service):
    def __init__(self, exchange:str, queue: str):
        self.exchange = exchange
        self.queue = queue

        self.connection_params = ConnectionParameters(
            host=os.getenv("RMQ_HOST"),
            port=int(os.getenv("RMQ_PORT")),
            credentials=PlainCredentials(os.getenv("RMQ_USERNAME"), os.getenv("RMQ_PASSWORD")),
            client_properties={"connection_name": os.getenv("HOSTNAME", "narrator-api")},
            heartbeat=20
        )

        self.publisher_connection: Optional[BlockingConnection] = None
        self.consumer_connection: Optional[BlockingConnection] = None

        self._reconnect = True
        self._connection_watchdog_thread = Thread(target=self._connect, daemon=True)
        self._connection_watchdog_thread.start()

        self.publisher_channel: Optional[BlockingChannel] = None
        self.consumer_watchdog_thread = Thread(target=self._consume, daemon=True)

        self.consumer_connection_lock = RLock()
        self._consumer_handlers = {}

    def reconnect_if_closed(self, conn: BlockingConnection):
        return conn if conn and conn.is_open else BlockingConnection(self.connection_params)

    def _connect(self):
        LOG.info("Connecting to RMQ...")

        while self._reconnect:
            try:
                self.publisher_connection = self.reconnect_if_closed(self.publisher_connection)
                self.publisher_connection.process_data_events()
                self.consumer_connection = self.reconnect_if_closed(self.consumer_connection)
                self.consumer_connection.process_data_events()
            except RuntimeError:
                LOG.exception("Failed to connect to RMQ.")
            time.sleep(1 + random.random())

    def configure(self, configure_callback):
        LOG.info("Configuring topology...")
        while self.publisher_connection is None:
            time.sleep(0.25)

        channel = self.publisher_connection.channel()
        configure_callback(channel)
        channel.close()

    def set_consumer(self, cls: type[RMQMessage], message_handler):
        """
        message_handler(payload, properties)
            - payload: RMQMessage
            - properties: spec.BasicProperties
        """
        self._consumer_handlers[cls.type] = {
            "type": cls.type,
            "type_class": cls,
            "handler": message_handler
        }

    def start_consuming(self):
        self.consumer_watchdog_thread.start()

    def _consume(self):
        def _message_handler(channel: BlockingChannel, method: Basic.Deliver, properties: BasicProperties, body: bytes):
            msg_type = properties.type
            LOG.debug("Handling message of type %s...", msg_type)

            if msg_type in self._consumer_handlers:
                consumer = self._consumer_handlers[msg_type]
                payload = consumer["type_class"].model_validate_json(body)
                try:
                    consumer["handler"](payload, properties)
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                except Exception:
                    LOG.exception(f"Error while handling message of type {msg_type}. Rejecting it...")
                    channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            else:
                LOG.info(f"Received message of type {msg_type}, but no handler is registered. Rejecting it...")
                channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

        while self._reconnect:
            try:
                ch = self._get_consumer_channel()
                ch.basic_qos(prefetch_count=1)
                ch.basic_consume(queue=self.queue, on_message_callback=_message_handler)
                ch.start_consuming()
            except ChannelError:
                LOG.exception("Error while consuming from RMQ.")
                time.sleep(1 + random.random())
                continue
            except AMQPChannelError:
                LOG.exception("Error while consuming from RMQ.")
                time.sleep(1 + random.random())
                continue

    def _get_consumer_channel(self):
        with self.consumer_connection_lock:
            conn = self.reconnect_if_closed(self.consumer_connection)
            return conn.channel()


    def _get_publisher_channel(self):
        if self.publisher_channel is None or not self.publisher_channel.is_open:
            self.publisher_channel = self.reconnect_if_closed(self.publisher_connection).channel()
            self.publisher_channel.confirm_delivery()
        return self.publisher_channel

    def publish(self, routing_key: str, payload: RMQMessage, properties: BasicProperties = None):
        channel = self._get_publisher_channel()
        body = payload.model_dump_json().encode("utf-8")
        props = properties or BasicProperties()
        props.type = payload.type
        channel.basic_publish(self.exchange, routing_key, body, props, mandatory=True)

    def close(self):
        LOG.info("Disconnecting from RMQ...")
        self._reconnect = False

        def _close_connection(connection: BlockingConnection):
            try:
                connection.close()
            except ConnectionWrongStateError:
                LOG.exception("Error while closing connection.")

        _close_connection(self.publisher_connection)
        _close_connection(self.consumer_connection)
