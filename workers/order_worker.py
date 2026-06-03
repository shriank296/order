import pika

from core.settings import get_app_settings
from db.session import get_database_session, get_engine

credentials = pika.PlainCredentials("user", "password")
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="localhost", credentials=credentials),
)
channel = connection.channel()

channel.queue_declare(
    queue="order",
    durable=True,
    arguments={"x-queue-type": "quorum"},
)


def process_order(ch, method, properties, body):
    settings = get_app_settings
    session = get_database_session(get_engine(settings))


channel.basic_consume(queue="order", on_message_callback=process_order)
