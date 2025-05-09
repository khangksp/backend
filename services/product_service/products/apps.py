from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'

    def ready(self):
        """
        Khởi động RabbitMQ consumer sau khi Django app registry sẵn sàng
        """
        try:
            from .rabbitmq import initialize_rabbitmq_consumer
            initialize_rabbitmq_consumer()
            logger.info("Đã gọi initialize_rabbitmq_consumer từ apps.py")
        except Exception as e:
            logger.error(f"Lỗi khi khởi động RabbitMQ consumer trong ready(): {str(e)}", exc_info=True)