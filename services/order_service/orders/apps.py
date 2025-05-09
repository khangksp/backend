# File: order_service/apps/orders/apps.py

from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    
    def ready(self):
        # Import and start RabbitMQ consumer
        try:
            from .rabbitmq import start_consumer_thread
            start_consumer_thread()
        except Exception as e:
            print(f"Error starting RabbitMQ consumer: {str(e)}")