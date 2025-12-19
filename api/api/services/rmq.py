import os
import random
import time
from threading import Thread
from typing import Optional

from pika import BlockingConnection, ConnectionParameters, BasicProperties, PlainCredentials
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import ConnectionWrongStateError
from pika.exchange_type import ExchangeType
from pydantic import BaseModel

from api import get_logger

LOG = get_logger(__name__)


class RMQClient:
    instance = None

    @staticmethod
    def create():
        """Returns a singleton instance of the RMQClient for FastAPI dependency injection."""
        if RMQClient.instance is None:
            RMQClient.instance = RMQClient()
        return RMQClient.instance

    def __init__(self):
        self.exchange = "narrator"
        self.queue = "api"
        self.publisher_connection: Optional[BlockingConnection] = None
        self.consumer_connection: Optional[BlockingConnection] = None

        self._reconnect = True
        self._connection_watchdog_thread = Thread(target=self._connect, daemon=True)
        self._connection_watchdog_thread.start()
        self.configure()

        self.publisher_channel: Optional[BlockingChannel] = None

    @staticmethod
    def reconnect_if_closed(conn: BlockingConnection, params: ConnectionParameters):
        return conn if conn and conn.is_open else BlockingConnection(params)

    def _connect(self):
        LOG.info("Connecting to RMQ...")

        params = ConnectionParameters(
            host=os.getenv("RMQ_HOST"),
            port=int(os.getenv("RMQ_PORT")),
            credentials=PlainCredentials(os.getenv("RMQ_USERNAME"), os.getenv("RMQ_PASSWORD")),
            client_properties={"connection_name": os.getenv("HOSTNAME", "narrator-api")}
        )

        while self._reconnect:
            try:
                self.publisher_connection = self.reconnect_if_closed(self.publisher_connection, params)
                self.consumer_connection = self.reconnect_if_closed(self.consumer_connection, params)
            except RuntimeError:
                LOG.exception("Failed to connect to RMQ.")
            time.sleep(1 + random.random())

    def configure(self):
        LOG.info("Configuring topology...")
        while self.publisher_connection is None:
            time.sleep(0.25)

        channel = self.publisher_connection.channel()
        channel.exchange_declare(self.exchange, ExchangeType.topic, durable=True)
        channel.queue_declare(self.queue, durable=True, arguments={"x-queue-type": "quorum"})
        channel.queue_bind(self.queue, self.exchange, routing_key="phonemes")
        channel.queue_bind(self.queue, self.exchange, routing_key="speech")
        channel.close()

    def add_consumer(self):
        # Add a new consumer and start consuming immediately.
        pass

    def _get_publisher_channel(self):
        if self.publisher_channel is None or not self.publisher_channel.is_open:
            self.publisher_channel = self.publisher_connection.channel()
            self.publisher_channel.confirm_delivery()
        return self.publisher_channel

    def publish(self, routing_key: str, payload: BaseModel, properties: BasicProperties = None):
        channel = self._get_publisher_channel()
        body = payload.model_dump_json().encode("utf-8")
        channel.basic_publish(self.exchange, routing_key, body, properties, mandatory=True)

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
