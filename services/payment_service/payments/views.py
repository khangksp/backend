import stripe
import json
import logging
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from payments.models import ThanhToan

logger = logging.getLogger(__name__)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session.get('metadata', {}).get('order_id')
        payment_intent_id = session.get('payment_intent')
        if not order_id or not payment_intent_id:
            logger.error("No order_id or payment_intent found in session metadata")
            return HttpResponse(status=400)

        try:
            with transaction.atomic():
                # Cập nhật hoặc tạo bản ghi ThanhToan
                thanh_toan, created = ThanhToan.objects.get_or_create(
                    fk_MaDonHang=order_id,
                    defaults={
                        'PhuongThucThanhToan': 'stripe',
                        'NgayThanhToan': timezone.now().date(),
                        'TrangThaiThanhToan': 'Hoàn tất',
                        'PaymentIntentId': payment_intent_id
                    }
                )
                if not created:
                    thanh_toan.TrangThaiThanhToan = 'Hoàn tất'
                    thanh_toan.NgayThanhToan = timezone.now().date()
                    thanh_toan.PaymentIntentId = payment_intent_id
                    thanh_toan.save()

                logger.info(f"Updated ThanhToan for order #{order_id}: {thanh_toan.pk_MaThanhToan}")

                # Cập nhật trạng thái DonHang qua API order_service
                response = requests.patch(
                    f'{settings.ORDER_SERVICE_URL}/orders/update/{order_id}/',
                    json={'status': 'Đã thanh toán'},
                    headers={'Authorization': f'Bearer {settings.INTERNAL_API_TOKEN}'}
                )
                if response.status_code != 200:
                    logger.error(f"Failed to update DonHang #{order_id}: {response.text}")
                    return HttpResponse(status=500)

                logger.info(f"Updated DonHang #{order_id} to status: Đã thanh toán")

        except Exception as e:
            logger.error(f"Error processing webhook for order #{order_id}: {str(e)}", exc_info=True)
            return HttpResponse(status=500)

    elif event['type'] in ['checkout.session.expired', 'charge.failed']:
        session = event['data']['object']
        order_id = session.get('metadata', {}).get('order_id')
        if not order_id:
            logger.error("No order_id found in session metadata")
            return HttpResponse(status=400)

        try:
            with transaction.atomic():
                # Cập nhật hoặc tạo bản ghi ThanhToan
                thanh_toan, created = ThanhToan.objects.get_or_create(
                    fk_MaDonHang=order_id,
                    defaults={
                        'PhuongThucThanhToan': 'stripe',
                        'NgayThanhToan': timezone.now().date(),
                        'TrangThaiThanhToan': 'Thất bại'
                    }
                )
                if not created:
                    thanh_toan.TrangThaiThanhToan = 'Thất bại'
                    thanh_toan.NgayThanhToan = timezone.now().date()
                    thanh_toan.save()

                logger.info(f"Updated ThanhToan for order #{order_id}: {thanh_toan.pk_MaThanhToan}")

                # Cập nhật trạng thái DonHang qua API order_service
                response = requests.patch(
                    f'{settings.ORDER_SERVICE_URL}/orders/update/{order_id}/',
                    json={'status': 'Thất bại'},
                    headers={'Authorization': f'Bearer {settings.INTERNAL_API_TOKEN}'}
                )
                if response.status_code != 200:
                    logger.error(f"Failed to update DonHang #{order_id}: {response.text}")
                    return HttpResponse(status=500)

                logger.info(f"Updated DonHang #{order_id} to status: Thất bại")

        except Exception as e:
            logger.error(f"Error processing webhook for order #{order_id}: {str(e)}", exc_info=True)
            return HttpResponse(status=500)

    return HttpResponse(status=200)

@csrf_exempt
def create_checkout_session(request):
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        amount = data.get('amount')
        items = data.get('items')

        if not all([order_id, amount, items]):
            logger.error("Missing required fields in checkout session request")
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        stripe.api_key = settings.STRIPE_SECRET_KEY

        line_items = [
            {
                'price_data': {
                    'currency': data.get('currency', 'vnd'),
                    'product_data': {
                        'name': item['TenSanPham'],
                    },
                    'unit_amount': int(item['GiaBan']),
                },
                'quantity': item['quantity'],
            }
            for item in items
        ]

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=f'{settings.FRONTEND_URL}/order-confirmation?order_id={order_id}',
            cancel_url=f'{settings.FRONTEND_URL}/checkout?payment_failed=true&order_id={order_id}',
            metadata={'order_id': order_id}
        )

        logger.info(f"Created Stripe checkout session for order #{order_id}: {session.id}")
        return JsonResponse({'session_id': session.id})

    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def refund_payment(request):
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')

        if not order_id:
            logger.error("Missing order_id in refund request")
            return JsonResponse({'error': 'Missing order_id'}, status=400)

        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Tìm bản ghi ThanhToan
        try:
            thanh_toan = ThanhToan.objects.get(fk_MaDonHang=order_id, PhuongThucThanhToan='stripe')
        except ThanhToan.DoesNotExist:
            logger.error(f"No ThanhToan record found for order #{order_id}")
            return JsonResponse({'error': 'No payment record found'}, status=404)

        if not thanh_toan.PaymentIntentId:
            logger.error(f"No PaymentIntentId found for order #{order_id}")
            return JsonResponse({'error': 'No PaymentIntentId available'}, status=400)

        # Tạo refund qua Stripe
        refund = stripe.Refund.create(
            payment_intent=thanh_toan.PaymentIntentId,
            reason='requested_by_customer'
        )

        # Cập nhật ThanhToan
        with transaction.atomic():
            thanh_toan.TrangThaiThanhToan = 'Hoàn tiền'
            thanh_toan.NgayThanhToan = timezone.now().date()
            thanh_toan.save()

            logger.info(f"Refunded ThanhToan for order #{order_id}: {refund.id}")

            # Cập nhật trạng thái DonHang qua API order_service
            response = requests.patch(
                f'{settings.ORDER_SERVICE_URL}/orders/update/{order_id}/',
                json={'status': 'Hoàn tiền'},
                headers={'Authorization': f'Bearer {settings.INTERNAL_API_TOKEN}'}
            )
            if response.status_code != 200:
                logger.error(f"Failed to update DonHang #{order_id}: {response.text}")
                return JsonResponse({'error': 'Failed to update order status'}, status=500)

            logger.info(f"Updated DonHang #{order_id} to status: Hoàn tiền")

        return JsonResponse({'message': 'Refund processed successfully', 'refund_id': refund.id})

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error during refund for order #{order_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error processing refund for order #{order_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)