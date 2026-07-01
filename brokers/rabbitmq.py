import json
import logging
from collections.abc import Callable
from typing import Annotated

import pika
from fastapi import Depends
from pika.exceptions import AMQPConnectionError

from core.settings import Settings, get_app_settings

logger = logging.getLogger(__name__)

RABBIT_MQ_BROKER: RabbitMq | None = None


class RabbitMq:
    def __init__(self, host: str, port: int, user_name: str, password: str):
        self.host = host
        self.port = port
        self.user_name = user_name
        self.password = password

    def connect(self):
        credentials = pika.PlainCredentials(self.user_name, self.password)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                connection_attempts=5,
                retry_delay=1,
            ),
        )
        self.connection = connection
        self.channel = self.connection.channel()

        logger.info(
            "Connected. is_open=%s",
            self.connection.is_open,
        )

    def __enter__(self):
        try:
            self.connect()
        except AMQPConnectionError:
            logger.exception("Faled to connect to rabbitmq")
            raise
        return self

    def send(self, queue_name: str, body: dict):
        self.channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        self.channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(body),
            properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
        )

    def publish(self, exchange: str, routing_key: str, body: dict):
        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(body),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent, headers={"retry": 0}
            ),
        )

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            logger.error(
                "An exception occured while using rabbitmq.",
                exc_info=(exc_type, exc, tb),
            )
        self.close_connection()

    def close(self):
        try:
            if self.connection and self.connection.is_open:
                self.connection.close()
        except Exception:
            logger.exception("Failed to close the connection")

    def receive(self, queue_name: str, callback: Callable):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue_name, on_message_callback=callback)
        self.channel.start_consuming()

    def create_order_topology(self):
        self.channel.exchange_declare(
            exchange="order_exchange", exchange_type="direct", durable=True
        )
        self.channel.queue_declare(
            queue="order_queue",
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        self.channel.queue_declare(
            queue="order_retry_queue",
            durable=True,
            arguments={
                "x-queue-type": "quorum",
                "x-message-ttl": 10000,
                "x-dead-letter-exchange": "order_exchange",
                "x-dead-letter-routing-key": "order.created",
            },
        )
        self.channel.queue_declare(
            queue="order_dlq",
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        self.channel.queue_bind(
            queue="order_queue", exchange="order_exchange", routing_key="order.created"
        )
        self.channel.queue_bind(
            queue="order_retry_queue",
            exchange="order_exchange",
            routing_key="order.retry",
        )
        self.channel.queue_bind(
            queue="order_dlq",
            exchange="order_exchange",
            routing_key="order.dlq",
        )

    def setup_topology(self):
        self.create_order_topology()


def get_message_broker(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> RabbitMq:
    global RABBIT_MQ_BROKER

    if not RABBIT_MQ_BROKER:
        RABBIT_MQ_BROKER = RabbitMq(
            settings.RMQ_HOST,
            settings.RMQ_PORT,
            settings.RMQ_USER,
            settings.RMQ_PASSWORD,
        )

    return RABBIT_MQ_BROKER
