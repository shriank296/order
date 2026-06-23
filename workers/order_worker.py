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
from exceptions import NonRetryableException, RetryableException
from services.order_processing import process_order

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

print(sys.path)
MAX_RETRY = 3


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
        except RetryableException:
            logger.exception("Order processing failed. It will be retried")
            retry_count = properties.headers.get("retry")
            logger.info(
                "Retry count: %s",
                retry_count,
            )
            if retry_count >= MAX_RETRY:
                ch.basic_publish(
                    exchange="order_exchange",
                    routing_key="order.dlq",
                    body=body,
                    properties=pika.BasicProperties(
                        delivery_mode=pika.DeliveryMode.Persistent,
                        headers={"retry": retry_count},
                    ),
                )
                logger.info("Message sent to DLQ after retries")
            else:
                retry_count += 1
                ch.basic_publish(
                    exchange="order_exchange",
                    routing_key="order.retry",
                    body=body,
                    properties=pika.BasicProperties(
                        delivery_mode=pika.DeliveryMode.Persistent,
                        headers={"retry": retry_count},
                    ),
                )
        except NonRetryableException:
            logger.exception("Order processing failed")
            ch.basic_publish(
                exchange="order_exchange",
                routing_key="order.dlq",
                body=body,
            )
            logger.info("Message sent to DLQ.")
        finally:
            ch.basic_ack(
                delivery_tag=method.delivery_tag,
            )


def worker():
    settings = get_app_settings()
    while True:
        broker = RabbitMq(settings.RMQ_HOST, settings.RMQ_USER, settings.RMQ_PASSWORD)
        broker.connect()
        broker.setup_topology()
        try:
            broker.receive(queue_name="order_queue", callback=callback)
        except Exception:
            logger.exception("Worker crashed")
        finally:
            broker.close()
        time.sleep(5)


if __name__ == "__main__":
    worker()
