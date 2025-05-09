import json
import pika
import logging
from django.conf import settings
import threading
import time
import os
from django.db import transaction
from .models import SanPham

# Cấu hình logging
logger = logging.getLogger(__name__)

# Cấu hình RabbitMQ từ settings
RABBITMQ_HOST = getattr(settings, 'RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_PORT = getattr(settings, 'RABBITMQ_PORT', 5672)
RABBITMQ_USER = getattr(settings, 'RABBITMQ_USER', 'guest')
RABBITMQ_PASS = getattr(settings, 'RABBITMQ_PASS', 'guest')

# Tên exchange và queue
PRODUCT_EXCHANGE = 'microservice_events'
PRODUCT_QUEUE = 'product_service_queue'

# Biến cờ để đánh dấu liệu RabbitMQ đã sẵn sàng
rabbitmq_available = False
consumer_thread = None
channel = None

def get_rabbitmq_connection():
    """
    Establish a connection to RabbitMQ
    """
    try:
        logger.debug(f"Connecting to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=int(RABBITMQ_PORT),
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        connection = pika.BlockingConnection(parameters)
        logger.info("Successfully connected to RabbitMQ")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {str(e)}", exc_info=True)
        return None

def publish_product_event(event_type, product_data):
    """
    Đăng sự kiện sản phẩm lên RabbitMQ exchange
    """
    global rabbitmq_available
    
    if not rabbitmq_available:
        logger.warning(f"RabbitMQ không khả dụng. Bỏ qua publish sự kiện {event_type}")
        return False
    
    try:
        connection = get_rabbitmq_connection()
        if not connection:
            rabbitmq_available = False
            logger.error("Không thể kết nối đến RabbitMQ để publish sự kiện")
            return False
        
        ch = connection.channel()
        
        ch.exchange_declare(exchange=PRODUCT_EXCHANGE, exchange_type='topic', durable=True)
        
        message = {
            'event_type': event_type,
            'product': product_data
        }
        
        ch.basic_publish(
            exchange=PRODUCT_EXCHANGE,
            routing_key=f"product.{event_type}",
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json'
            )
        )
        
        connection.close()
        logger.info(f"Đã publish sự kiện {event_type} cho sản phẩm ID: {product_data.get('id')}")
        return True
    except Exception as e:
        rabbitmq_available = False
        logger.error(f"Lỗi khi publish sự kiện sản phẩm: {str(e)}", exc_info=True)
        return False

def start_consumer_thread():
    """
    Khởi động consumer thread
    """
    global channel
    if channel is not None:
        try:
            channel.start_consuming()
        except Exception as e:
            logger.error(f"Consumer bị ngắt: {str(e)}")
            time.sleep(5)
            setup_rabbitmq_consumer()
    else:
        logger.error("Không thể khởi động consumer thread: channel is None")

def setup_rabbitmq_consumer():
    """
    Thiết lập consumer để nhận các sự kiện từ các service khác
    """
    global rabbitmq_available, consumer_thread, channel
    
    if os.environ.get('RUNNING_IN_DOCKER', 'False') == 'True':
        try:
            connection = get_rabbitmq_connection()
            if not connection:
                logger.error("Không thể kết nối đến RabbitMQ để thiết lập consumer")
                return False
            
            channel = connection.channel()
            
            channel.exchange_declare(exchange=PRODUCT_EXCHANGE, exchange_type='topic', durable=True)
            result = channel.queue_declare(queue=PRODUCT_QUEUE, durable=True)
            queue_name = result.method.queue
            
            routing_keys = ['order.created', 'order.cancelled']
            for routing_key in routing_keys:
                channel.queue_bind(exchange=PRODUCT_EXCHANGE, queue=queue_name, routing_key=routing_key)
            
            def callback(ch, method, properties, body):
                """
                Xử lý các sự kiện RabbitMQ
                """
                try:
                    data = json.loads(body)
                    logger.info(f"Đã nhận sự kiện: {method.routing_key}")
                    
                    if method.routing_key == 'order.created':
                        items = data.get('items', [])
                        with transaction.atomic():
                            for item in items:
                                product_id = item.get('product_id')
                                quantity = item.get('quantity')
                                
                                try:
                                    product = SanPham.objects.select_for_update().get(id=product_id)
                                    if product.SoLuongTon >= quantity:
                                        product.SoLuongTon -= quantity
                                        product.save()
                                        logger.info(f"Updated stock for product {product_id}: new stock = {product.SoLuongTon}")
                                    else:
                                        logger.error(f"Insufficient stock for product {product_id}: required {quantity}, available {product.SoLuongTon}")
                                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                                        return
                                except SanPham.DoesNotExist:
                                    logger.error(f"Product {product_id} not found")
                                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                                    return
                    
                    elif method.routing_key == 'order.cancelled':
                        items = data.get('items', [])
                        with transaction.atomic():
                            for item in items:
                                product_id = item.get('product_id')
                                quantity = item.get('quantity')
                                
                                try:
                                    product = SanPham.objects.select_for_update().get(id=product_id)
                                    product.SoLuongTon += quantity
                                    product.save()
                                    logger.info(f"Restored stock for product {product_id}: new stock = {product.SoLuongTon}")
                                except SanPham.DoesNotExist:
                                    logger.error(f"Product {product_id} not found")
                                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                                    return
                    
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý message: {str(e)}", exc_info=True)
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue_name, on_message_callback=callback)
            
            consumer_thread = threading.Thread(target=start_consumer_thread)
            consumer_thread.daemon = True
            consumer_thread.start()
            
            rabbitmq_available = True
            logger.info("Đã khởi động RabbitMQ consumer")
            return True
        except Exception as e:
            rabbitmq_available = False
            logger.error(f"Lỗi khi thiết lập RabbitMQ consumer: {str(e)}", exc_info=True)
            return False
    else:
        logger.info("Không chạy trong Docker, bỏ qua kết nối RabbitMQ")
        return False

def initialize_rabbitmq_consumer():
    """
    Khởi động consumer RabbitMQ với cơ chế thử lại
    """
    if os.environ.get('RUNNING_IN_DOCKER', 'False') == 'True':
        try:
            max_retries = 5
            retry_delay = 5
            for attempt in range(max_retries):
                if setup_rabbitmq_consumer():
                    break
                logger.warning(f"Thử kết nối RabbitMQ lần {attempt + 1} thất bại, thử lại sau {retry_delay} giây")
                time.sleep(retry_delay)
            else:
                logger.error("Không thể khởi động RabbitMQ consumer sau nhiều lần thử")
        except Exception as e:
            logger.error(f"Lỗi khởi động RabbitMQ consumer: {str(e)}", exc_info=True)
    else:
        logger.info("Phát hiện môi trường local, không khởi động RabbitMQ consumer")