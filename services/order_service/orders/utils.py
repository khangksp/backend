import json
import pika
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class RabbitMQClient:
    """
    Client for RabbitMQ messaging
    """
    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()
    
    def connect(self, max_retries=3, retry_delay=2):
        for attempt in range(max_retries):
            try:
                credentials = pika.PlainCredentials(
                    settings.RABBITMQ_USER,
                    settings.RABBITMQ_PASS
                )
                parameters = pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                self.channel.exchange_declare(
                    exchange='microservice_events',
                    exchange_type='topic',
                    durable=True
                )
                logger.info("Connected to RabbitMQ successfully")
                return True
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed to connect to RabbitMQ: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        logger.error(f"Failed to connect to RabbitMQ after {max_retries} attempts")
        return False
    
    def publish(self, routing_key, message):
        try:
            if not self.connection or self.connection.is_closed or not self.channel or self.channel.is_closed:
                if not self.connect():
                    logger.error("Cannot publish: Failed to reconnect to RabbitMQ")
                    return False
            self.channel.basic_publish(
                exchange='microservice_events',
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            logger.info(f"Published message to {routing_key}: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to {routing_key}: {str(e)}", exc_info=True)
            return False
    def consume(self, queue_name, routing_keys, callback):
        """
        Consume messages from a queue
        
        Args:
            queue_name (str): Name of the queue to consume from
            routing_keys (list): List of routing keys to bind to
            callback (function): Callback function for processing messages
        """
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()
            
            # Declare queue
            self.channel.queue_declare(
                queue=queue_name,
                durable=True
            )
            
            # Bind queue to exchange with routing keys
            for routing_key in routing_keys:
                self.channel.queue_bind(
                    exchange='microservice_events',
                    queue=queue_name,
                    routing_key=routing_key
                )
            
            # Set up consumer
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=False
            )
            
            logger.info(f"Started consuming from queue {queue_name} with routing keys {routing_keys}")
            
            # Start consuming
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Failed to start consuming: {str(e)}")
    
    def close(self):
        """
        Close the connection to RabbitMQ
        """
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("Closed RabbitMQ connection")

# Utility function to get RabbitMQ client instance
def get_rabbitmq_client():
    return RabbitMQClient()