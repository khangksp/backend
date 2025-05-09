from django.apps import AppConfig

class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'

    def ready(self):
        import os
        # Chỉ khởi động consumer trong môi trường không phải test
        if os.environ.get('RUN_MAIN', None) == 'true':
            from .rabbitmq import start_consumer_thread
            try:
                start_consumer_thread()
            except Exception as e:
                from .rabbitmq import logger
                logger.error(f"Failed to start RabbitMQ consumer thread: {str(e)}", exc_info=True)