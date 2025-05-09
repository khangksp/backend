from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .rabbitmq import publish_order_event
from .models import DonHang, ChiTietDonHang, TrangThai
from .serializers import DonHangSerializer, ChiTietDonHangSerializer, CreateOrderSerializer
from django.db.models import Sum, Count
import json
import logging
import requests
from decimal import Decimal

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def count_orders(request):
    """API đếm tổng số đơn hàng"""
    try:
        total_orders = DonHang.objects.count()
        return Response({
            'status': 'success',
            'total_orders': total_orders
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Lỗi khi đếm đơn hàng: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Lỗi khi đếm đơn hàng: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def list_orders(request):
    """API lấy danh sách tất cả đơn hàng"""
    try:
        orders = DonHang.objects.all().order_by('-NgayDatHang')
        serializer = DonHangSerializer(orders, many=True)
        return Response({
            'status': 'success',
            'orders': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách đơn hàng: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Lỗi khi lấy danh sách đơn hàng: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_order_info(request, user_id):
    """
    API lấy thông tin tổng quan về các đơn hàng của một người dùng
    """
    try:
        orders = DonHang.objects.filter(MaNguoiDung=user_id).order_by('-NgayDatHang')
        total_orders = orders.count()
        total_amount = orders.aggregate(total=Sum('TongTien'))['total'] or 0.0
        orders_serializer = DonHangSerializer(orders, many=True)
        order_status_summary = orders.values('MaTrangThai__TenTrangThai').annotate(
            count=Count('MaDonHang'),
            total_amount=Sum('TongTien')
        )
        order_status_summary_list = []
        for summary in order_status_summary:
            summary_dict = dict(summary)
            summary_dict['total_amount'] = float(summary_dict['total_amount']) if summary_dict['total_amount'] is not None else 0.0
            order_status_summary_list.append(summary_dict)
        
        return Response({
            'status': 'success',
            'total_orders': total_orders,
            'total_amount': float(total_amount),
            'orders': orders_serializer.data,
            'order_status_summary': order_status_summary_list
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin đơn hàng theo user ID: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Lỗi khi lấy thông tin đơn hàng: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DonHangViewSet(viewsets.ModelViewSet):
    queryset = DonHang.objects.all()
    serializer_class = DonHangSerializer

    def get_queryset(self):
        """Lọc đơn hàng theo người dùng nếu có tham số user_id"""
        queryset = DonHang.objects.all()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(MaNguoiDung=user_id)
        return queryset

class CreateOrderView(APIView):
    """API View để tạo đơn hàng mới từ giỏ hàng"""

    def post(self, request):
        logger.info(f"Nhận request tạo đơn hàng: {request.data}")

        token_user_id = getattr(request.user, 'id', None)
        logger.info(f"User ID từ token: {token_user_id}")

        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)

        if (not data.get('user_id') or data.get('user_id') is None) and token_user_id:
            data['user_id'] = token_user_id
            logger.info(f"Sử dụng user_id từ token: {token_user_id}")
        elif not data.get('user_id') or data.get('user_id') is None:
            data['user_id'] = 1
            logger.info("Không tìm thấy user_id, sử dụng giá trị mặc định: 1")

        if 'user_id' in data and not isinstance(data['user_id'], int):
            try:
                data['user_id'] = int(data['user_id'])
                logger.info(f"Chuyển đổi user_id thành int: {data['user_id']}")
            except (ValueError, TypeError):
                data['user_id'] = 1
                logger.info("Không thể chuyển đổi user_id thành int, sử dụng giá trị mặc định: 1")

        serializer = CreateOrderSerializer(data=data)

        if serializer.is_valid():
            data = serializer.validated_data
            logger.info(f"Dữ liệu hợp lệ: {data}")

            try:
                trang_thai, created = TrangThai.objects.get_or_create(
                    TenTrangThai="Đang xử lý",
                    defaults={'LoaiTrangThai': 'Đơn hàng'}
                )

                total_amount = Decimal('0')
                for item in data['items']:
                    price = item.get('price') or item.get('GiaBan') or item.get('GiaSanPham')
                    quantity = item.get('quantity')

                    if price is not None and quantity is not None:
                        try:
                            price = Decimal(str(price))
                            quantity = Decimal(str(quantity))
                            total_amount += price * quantity
                            logger.info(f"Sản phẩm: {item.get('name', item.get('TenSanPham', 'N/A'))}, Giá: {price}, SL: {quantity}")
                        except (ValueError, TypeError) as e:
                            logger.error(f"Lỗi khi tính giá sản phẩm {item.get('TenSanPham', 'N/A')}: {str(e)}")
                            return Response({
                                'status': 'error',
                                'message': f'Giá hoặc số lượng không hợp lệ cho sản phẩm: {item.get("TenSanPham", "N/A")}'
                            }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        logger.warning(f"Thiếu thông tin giá hoặc số lượng cho sản phẩm: {item}")
                        return Response({
                            'status': 'error',
                            'message': f'Thiếu thông tin giá hoặc số lượng cho sản phẩm: {item.get("TenSanPham", "N/A")}'
                        }, status=status.HTTP_400_BAD_REQUEST)

                logger.info(f"Tổng tiền đơn hàng: {total_amount}")

                if data.get('payment_method', '').lower() == 'ewallet':
                    auth_header = request.META.get('HTTP_AUTHORIZATION') or request.headers.get('Authorization')
                    if not auth_header:
                        logger.warning("Thiếu Authorization header khi gọi API ví điện tử")

                    headers = {
                        'Authorization': auth_header,
                        'Content-Type': 'application/json'
                    }

                    logger.info(f"Gửi request tới ewallet với headers: {headers}, body: {{'tongtien': {float(total_amount)}}}")

                    try:
                        ewallet_response = requests.post(
                            'http://api_gateway:8000/api/auth/balance/reduce/',
                            json={'tongtien': float(total_amount)},
                            headers=headers
                        )

                        logger.info(f"Mã trạng thái: {ewallet_response.status_code}")
                        logger.info(f"Nội dung phản hồi: {ewallet_response.text}")

                        if ewallet_response.status_code != 200:
                            logger.error(f"Lỗi thanh toán ví điện tử: {ewallet_response.text}")
                            try:
                                error_details = ewallet_response.json()
                            except ValueError:
                                error_details = {'message': 'Không thể phân tích phản hồi từ API trừ tiền'}
                            return Response({
                                'status': 'error',
                                'message': error_details.get('message', 'Thanh toán bằng ví điện tử thất bại'),
                                'error_details': error_details
                            }, status=status.HTTP_400_BAD_REQUEST)

                    except requests.RequestException as e:
                        logger.error(f"Lỗi kết nối API trừ tiền: {str(e)}")
                        return Response({
                            'status': 'error',
                            'message': 'Lỗi kết nối thanh toán'
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                don_hang = DonHang.objects.create(
                    MaNguoiDung=data['user_id'],
                    MaTrangThai=trang_thai,
                    TongTien=total_amount,
                    DiaChi=data['address'],
                    TenNguoiNhan=data['recipient_name'],
                    SoDienThoai=data['phone_number'],
                    PhuongThucThanhToan=data['payment_method']
                )

                chi_tiet_items = []
                for item in data['items']:
                    price = item.get('price', item.get('GiaBan', item.get('GiaSanPham', 0)))
                    ten_san_pham = item.get('name', item.get('TenSanPham', ''))
                    hinh_anh = item.get('image_url', item.get('HinhAnh_URL', ''))

                    chi_tiet = ChiTietDonHang.objects.create(
                        MaDonHang=don_hang,
                        MaSanPham=item.get('id'),
                        SoLuong=item.get('quantity', 1),
                        GiaSanPham=price,
                        TenSanPham=ten_san_pham,
                        HinhAnh=hinh_anh
                    )
                    chi_tiet_items.append({
                        'product_id': chi_tiet.MaSanPham,
                        'quantity': chi_tiet.SoLuong
                    })

                order_data = {
                    'order_id': don_hang.MaDonHang,
                    'user_id': don_hang.MaNguoiDung,
                    'status': don_hang.MaTrangThai.TenTrangThai,
                    'total_amount': float(don_hang.TongTien),
                    'payment_method': don_hang.PhuongThucThanhToan,
                    'recipient_name': don_hang.TenNguoiNhan,
                    'phone_number': don_hang.SoDienThoai,
                    'address': don_hang.DiaChi,
                    'items': chi_tiet_items
                }
                publish_order_event('created', order_data)
                logger.info(f"Đã gửi sự kiện order.created cho đơn hàng #{don_hang.MaDonHang}")

                return Response({
                    'order_id': don_hang.MaDonHang,
                    'status': 'success',
                    'message': 'Đơn hàng đã được tạo thành công',
                    'total_amount': float(don_hang.TongTien)
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Lỗi khi tạo đơn hàng: {str(e)}", exc_info=True)
                return Response({
                    'status': 'error',
                    'message': f'Lỗi khi tạo đơn hàng: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.warning(f"Lỗi dữ liệu đầu vào: {serializer.errors}")
        return Response({
            'status': 'error',
            'message': 'Dữ liệu không hợp lệ',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_user_orders(request, user_id):
    """Lấy danh sách đơn hàng của một người dùng cụ thể"""
    orders = DonHang.objects.filter(MaNguoiDung=user_id).order_by('-NgayDatHang')
    serializer = DonHangSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_order_details(request, order_id):
    """Lấy chi tiết một đơn hàng cụ thể"""
    try:
        order = DonHang.objects.get(MaDonHang=order_id)
        order_data = DonHangSerializer(order).data
        order_items = ChiTietDonHang.objects.filter(MaDonHang=order)
        order_items_data = ChiTietDonHangSerializer(order_items, many=True).data
        
        return Response({
            'order': order_data,
            'items': order_items_data
        })
    except DonHang.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Đơn hàng không tồn tại'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT'])
@permission_classes([AllowAny])
def update_order_status(request, order_id):
    """
    API để cập nhật trạng thái của một đơn hàng
    """
    try:
        order = DonHang.objects.get(MaDonHang=order_id)
        new_status_id = request.data.get('MaTrangThai')
        if not new_status_id:
            logger.error(f"Thiếu MaTrangThai trong request cho đơn hàng #{order_id}")
            return Response({
                'status': 'error',
                'message': 'Vui lòng cung cấp MaTrangThai'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            new_status = TrangThai.objects.get(MaTrangThai=new_status_id)
        except TrangThai.DoesNotExist:
            logger.error(f"Trạng thái với MaTrangThai={new_status_id} không tồn tại")
            return Response({
                'status': 'error',
                'message': f'Trạng thái với MaTrangThai={new_status_id} không tồn tại'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        old_status_id = order.MaTrangThai.MaTrangThai
        old_status_name = order.MaTrangThai.TenTrangThai
        
        # Validate status transitions
        if old_status_id in [6, 7]:
            logger.warning(f"Không thể cập nhật trạng thái đơn hàng #{order_id} với trạng thái hiện tại {old_status_name}")
            return Response({
                'status': 'error',
                'message': 'Không thể cập nhật trạng thái của đơn hàng đã hủy hoặc đã hoàn tiền'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_status_id == 6 and old_status_id != 3:
            logger.warning(f"Chỉ đơn hàng đang xử lý mới có thể hủy, đơn hàng #{order_id} hiện tại: {old_status_name}")
            return Response({
                'status': 'error',
                'message': 'Chỉ đơn hàng đang xử lý mới có thể được hủy'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if old_status_id == 5 and new_status_id != 7:
            logger.warning(f"Đơn hàng đã giao #{order_id} chỉ có thể chuyển sang trạng thái hoàn tiền")
            return Response({
                'status': 'error',
                'message': 'Đơn hàng đã giao chỉ có thể được cập nhật sang trạng thái hoàn tiền'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.MaTrangThai = new_status
        order.save()
        
        # Prepare order items for the event
        order_items = ChiTietDonHang.objects.filter(MaDonHang=order)
        chi_tiet_items = [
            {
                'product_id': item.MaSanPham,
                'quantity': item.SoLuong,
                'price': float(item.GiaSanPham),
                'name': item.TenSanPham,
                'image_url': item.HinhAnh
            } for item in order_items
        ]
        
        # Prepare order data for events
        order_data = {
            'order_id': order.MaDonHang,
            'user_id': order.MaNguoiDung,
            'old_status': old_status_name,
            'new_status': new_status.TenTrangThai,
            'total_amount': float(order.TongTien),
            'payment_method': order.PhuongThucThanhToan,
            'recipient_name': order.TenNguoiNhan,
            'phone_number': order.SoDienThoai,
            'address': order.DiaChi,
            'items': chi_tiet_items
        }
        
        # Publish order.status_updated event
        try:
            publish_order_event('status_updated', order_data)
            logger.info(f"Đã gửi sự kiện order.status_updated cho đơn hàng #{order.MaDonHang}")
        except Exception as e:
            logger.error(f"Lỗi khi gửi sự kiện order.status_updated cho đơn hàng #{order.MaDonHang}: {str(e)}", exc_info=True)
        
        # Publish order.cancelled event if status is changed to Cancelled (MaTrangThai: 6)
        if new_status_id == 6:
            try:
                publish_order_event('cancelled', order_data)
                logger.info(f"Đã gửi sự kiện order.cancelled cho đơn hàng #{order.MaDonHang}")
            except Exception as e:
                logger.error(f"Lỗi khi gửi sự kiện order.cancelled cho đơn hàng #{order.MaDonHang}: {str(e)}", exc_info=True)
        
        serializer = DonHangSerializer(order)
        
        return Response({
            'status': 'success',
            'message': f'Cập nhật trạng thái đơn hàng #{order_id} thành {new_status.TenTrangThai}',
            'order': serializer.data
        }, status=status.HTTP_200_OK)
    
    except DonHang.DoesNotExist:
        logger.error(f"Đơn hàng #{order_id} không tồn tại")
        return Response({
            'status': 'error',
            'message': f'Đơn hàng #{order_id} không tồn tại'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật trạng thái đơn hàng #{order_id}: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Lỗi khi cập nhật trạng thái đơn hàng: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)