import json

import pika


class RabbitMq:
    def __init__(self, host: str, user_name: str, password: str):
        self.host = host
        self.user_name = user_name
        self.password = password
        self._connect()

    def _connect(self):
        credentials = pika.PlainCredentials(self.user_name, self.password)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.host, credentials=credentials),
        )
        self.connection = connection
        self.channel = self.connection.channel()

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
        )

    def close_connection(self):
        self.connection.close()
