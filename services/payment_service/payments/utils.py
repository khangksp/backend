
#payment_service/payments/utils.py
import pika
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        try:
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD
            )
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                credentials=credentials
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange='microservice_events', exchange_type='topic', durable=True)
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    def publish(self, routing_key, message):
        try:
            self.channel.basic_publish(
                exchange='microservice_events',
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)  # Persistent
            )
            logger.info(f"Published message to {routing_key}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            self.connect()
            self.channel.basic_publish(
                exchange='microservice_events',
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)
            )

    def consume(self, queue_name, routing_keys, callback):
        try:
            self.channel.queue_declare(queue=queue_name, durable=True)
            for routing_key in routing_keys:
                self.channel.queue_bind(
                    queue=queue_name,
                    exchange='microservice_events',
                    routing_key=routing_key
                )
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback
            )
            logger.info(f"Started consuming from queue {queue_name}")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Error in consumer: {str(e)}")
            self.connect()
            self.consume(queue_name, routing_keys, callback)

    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()

def get_rabbitmq_client():
    return RabbitMQClient()