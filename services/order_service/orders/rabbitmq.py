# File: order_service/apps/orders/rabbitmq.py

import json
import threading
import logging
from django.conf import settings
import time
from .utils import get_rabbitmq_client
from .models import DonHang as Order, ChiTietDonHang as OrderItem

logger = logging.getLogger(__name__)

def message_callback(ch, method, properties, body):
    """
    Callback function for processing incoming messages from RabbitMQ
    """
    try:
        message = json.loads(body)
        routing_key = method.routing_key
        
        logger.info(f"Received message with routing key {routing_key}: {message}")
        
        # Process message based on routing key
        if routing_key == 'product.stock_changed':
            # Example: Check if any pending orders can be fulfilled now
            product_id = message.get('product_id')
            new_stock = message.get('new_stock', 0)
            if product_id and new_stock > 0:
                # Find pending orders with this product
                order_items = OrderItem.objects.filter(
                    MaSanPham=product_id,
                    MaDonHang__MaTrangThai__TenTrangThai='Chờ xử lý'
                )
                
                for item in order_items:
                    if new_stock >= item.SoLuong:
                        # We can fulfill this order item
                        order = item.MaDonHang
                        
                        # Update order status to "Đang xử lý"
                        from .models import TrangThai
                        processing_status = TrangThai.objects.get(TenTrangThai='Đang xử lý')
                        order.MaTrangThai = processing_status
                        order.save()
                        
                        # Publish order updated event
                        publish_order_event('updated', {
                            'order_id': order.MaDonHang,
                            'user_id': order.MaNguoiDung,
                            'status': order.MaTrangThai.TenTrangThai,
                            'total_amount': float(order.TongTien),
                            'items': [
                                {
                                    'product_id': chi_tiet.MaSanPham,
                                    'quantity': chi_tiet.SoLuong
                                } for chi_tiet in order.chi_tiet.all()
                            ]
                        })
                        
                        logger.info(f"Order #{order.MaDonHang} status updated to PROCESSING")
                        
                        # Reduce available stock for next iteration
                        new_stock -= item.SoLuong
                        if new_stock <= 0:
                            break
        
        # Acknowledge message
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        # Reject message
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_consumer():
    """
    Start consuming messages from RabbitMQ
    """
    try:
        client = get_rabbitmq_client()
        
        # Order service is interested in product and user events
        queue_name = 'order_service_queue'
        routing_keys = ['product.stock_changed', 'product.updated', 'product.deleted', 'user.updated']
        
        client.consume(queue_name, routing_keys, message_callback)
    except Exception as e:
        logger.error(f"Error starting RabbitMQ consumer: {str(e)}")

def publish_order_event(event_type, order_data, max_retries=3, retry_delay=2):
    """
    Publish an order-related event to RabbitMQ with retry mechanism
    """
    logger.debug(f"Preparing to publish {event_type} event: {order_data}")
    try:
        client = get_rabbitmq_client()
        logger.debug("Got RabbitMQ client")
        routing_key = f"order.{event_type}"
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1} to publish to {routing_key}")
                success = client.publish(routing_key, order_data)
                if success:
                    logger.info(f"Successfully published {routing_key} event: {order_data}")
                    client.close()
                    return True
                logger.warning(f"Attempt {attempt + 1} failed to publish {routing_key}")
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} error: {str(e)}", exc_info=True)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        logger.error(f"Failed to publish {routing_key} after {max_retries} attempts")
        client.close()
        return False
    except Exception as e:
        logger.error(f"Error initializing client for {routing_key}: {str(e)}", exc_info=True)
        return False

def start_consumer_thread():
    """
    Start RabbitMQ consumer in a separate thread
    """
    try:
        consumer_thread = threading.Thread(target=start_consumer)
        consumer_thread.daemon = True
        consumer_thread.start()
        logger.info("Started RabbitMQ consumer thread")
    except Exception as e:
        logger.error(f"Error starting consumer thread: {str(e)}")