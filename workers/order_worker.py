import json
import logging
import sys
import time

import pika
from pika import BasicProperties
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from brokers.rabbitmq import RabbitMq
from core.settings import get_app_settings
from db.session import get_database_session, get_engine, get_session_factory
from services.order_processing import process_order

logger = logging.getLogger(__name__)

print(sys.path)


def callback(
    ch: BlockingChannel,
    method: Basic.Deliver,
    properties: BasicProperties,
    body: bytes,
):
    settings = get_app_settings()
    session_factory = get_session_factory(settings)
    with session_factory() as session:
        try:
            payload = json.loads(body.decode())
            process_order(payload, session)
            ch.basic_ack(
                delivery_tag=method.delivery_tag,
            )
        except Exception:
            logger.exception("Order processing failed.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def worker():
    settings = get_app_settings()
    while True:
        broker = RabbitMq(settings.RMQ_HOST, settings.RMQ_USER, settings.RMQ_PASSWORD)
        broker.connect()
        try:
            broker.receive(queue_name="order", callback=callback)
        except Exception:
            logger.exception("Worker crashed")
        finally:
            broker.close()
        time.sleep(5)


if __name__ == "__main__":
    worker()
