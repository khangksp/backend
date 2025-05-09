from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import TaiKhoan, NguoiDung
from .serializers import TaiKhoanSerializer
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal, InvalidOperation

import logging

logger = logging.getLogger(__name__)
class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # if request.user.loaiquyen != 'admin':
        #     return Response(
        #         {"status": "error", "message": "Chỉ admin mới được xem danh sách người dùng"},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        users = TaiKhoan.objects.all()
        serializer = TaiKhoanSerializer(users, many=True)
        return Response({"status": "ok", "users": serializer.data})

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        tendangnhap = request.data.get('tendangnhap')
        password = request.data.get('password')

        if not tendangnhap or not password:
            return Response(
                {"status": "error", "message": "Tên đăng nhập và mật khẩu là bắt buộc"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            taikhoan = TaiKhoan.objects.get(tendangnhap=tendangnhap)
            if taikhoan.check_password(password):
                taikhoan.last_login = timezone.now()
                taikhoan.save(update_fields=['last_login'])
                refresh = RefreshToken.for_user(taikhoan)
                serializer = TaiKhoanSerializer(taikhoan)
                user_data = serializer.data
                user_data.pop('nguoidung', None)  # Loại bỏ nguoidung (write_only)

                return Response({
                    "status": "ok",
                    "message": "Đăng nhập thành công",
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": user_data
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"status": "error", "message": "Mật khẩu không đúng"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except TaiKhoan.DoesNotExist:
            return Response(
                {"status": "error", "message": "Tên đăng nhập không tồn tại"},
                status=status.HTTP_401_UNAUTHORIZED
            )

class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        # if request.user.loaiquyen != 'admin':
        #     return Response(
        #         {"status": "error", "message": "Chỉ admin mới được tạo người dùng"},
        #         status=status.HTTP_403_FORBIDDEN
        #     )

        serializer = TaiKhoanSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            user_data = serializer.data
            user_data.pop('nguoidung', None)  # Loại bỏ nguoidung (write_only)
            return Response(
                {"status": "ok", "message": "Tạo người dùng thành công", "user": user_data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"status": "error", "message": "Tạo người dùng thất bại", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
class UserUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, user_id):
        taikhoan = get_object_or_404(TaiKhoan, mataikhoan=user_id)
        is_admin = request.user.loaiquyen == 'admin'
        is_self = request.user.mataikhoan == user_id

        if not (is_self or is_admin):
            return Response(
                {"status": "error", "message": "Bạn không có quyền sửa thông tin người dùng này"},
                status=status.HTTP_403_FORBIDDEN
            )

        tendangnhap = request.data.get('tendangnhap')
        password = request.data.get('password')
        loaiquyen = request.data.get('loaiquyen')
        nguoidung_data = request.data.get('nguoidung', {})
        tennguoidung = nguoidung_data.get('tennguoidung')
        email = nguoidung_data.get('email')
        sodienthoai = nguoidung_data.get('sodienthoai')
        diachi = nguoidung_data.get('diachi')

        if not is_admin:
            if any([tendangnhap, password, loaiquyen]):
                return Response(
                    {"status": "error", "message": "Chỉ admin mới được cập nhật tên đăng nhập, mật khẩu hoặc loại quyền"},
                    status=status.HTTP_403_FORBIDDEN
                )

        nguoidung = taikhoan.nguoidung.first()
        if not nguoidung and any([tennguoidung, email, sodienthoai, diachi]):
            nguoidung = NguoiDung(fk_taikhoan=taikhoan)

        if tendangnhap and is_admin:
            if TaiKhoan.objects.exclude(mataikhoan=taikhoan.mataikhoan).filter(tendangnhap=tendangnhap).exists():
                return Response(
                    {"status": "error", "message": "Tên đăng nhập đã được sử dụng bởi người dùng khác"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            taikhoan.tendangnhap = tendangnhap

        if password and is_admin:
            if len(password) < 6:
                return Response(
                    {"status": "error", "message": "Mật khẩu phải có ít nhất 6 ký tự"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            taikhoan.set_password(password)

        if loaiquyen and is_admin:
            VALID_ROLES = ['admin', 'khach', 'nhanvien']
            if loaiquyen not in VALID_ROLES:
                return Response(
                    {"status": "error", "message": f"Loại quyền '{loaiquyen}' không hợp lệ. Chỉ chấp nhận: {', '.join(VALID_ROLES)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            taikhoan.loaiquyen = loaiquyen

        if nguoidung:
            if tennguoidung is not None:
                if not tennguoidung and nguoidung.tennguoidung:
                    return Response(
                        {"status": "error", "message": "Tên người dùng không được để trống"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                nguoidung.tennguoidung = tennguoidung

            if email is not None:
                if not email and nguoidung.email:
                    return Response(
                        {"status": "error", "message": "Email không được để trống"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if email and NguoiDung.objects.exclude(fk_taikhoan=taikhoan).filter(email=email).exists():
                    return Response(
                        {"status": "error", "message": "Email đã được sử dụng"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                nguoidung.email = email

            if sodienthoai is not None:
                if not sodienthoai and nguoidung.sodienthoai:
                    return Response(
                        {"status": "error", "message": "Số điện thoại không được để trống"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if sodienthoai and NguoiDung.objects.exclude(fk_taikhoan=taikhoan).filter(sodienthoai=sodienthoai).exists():
                    return Response(
                        {"status": "error", "message": "Số điện thoại đã được sử dụng"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                nguoidung.sodienthoai = sodienthoai

            if diachi is not None:
                nguoidung.diachi = diachi

        try:
            taikhoan.save()
            if nguoidung:
                nguoidung.save()
        except Exception as e:
            return Response(
                {"status": "error", "message": f"Lỗi khi lưu dữ liệu: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        serializer = TaiKhoanSerializer(taikhoan)
        user_data = serializer.data
        user_data.pop('nguoidung', None)

        return Response({
            "status": "ok",
            "message": "Cập nhật thông tin người dùng thành công",
            "user": user_data
        }, status=status.HTTP_200_OK)
class UserDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):
        if request.user.loaiquyen != 'admin':
            return Response(
                {"status": "error", "message": "Chỉ admin mới được xóa người dùng"},
                status=status.HTTP_403_FORBIDDEN
            )

        taikhoan = get_object_or_404(TaiKhoan, mataikhoan=user_id)
        if taikhoan.loaiquyen == 'admin' and TaiKhoan.objects.filter(loaiquyen='admin').count() <= 1:
            return Response(
                {"status": "error", "message": "Không thể xóa admin cuối cùng"},
                status=status.HTTP_400_BAD_REQUEST
            )

        taikhoan.delete()
        return Response({
            "status": "ok",
            "message": f"Đã xóa người dùng {taikhoan.tendangnhap} thành công"
        }, status=status.HTTP_200_OK)

class UserDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        taikhoan = get_object_or_404(TaiKhoan, mataikhoan=user_id)

        # if request.user.loaiquyen != 'admin' and request.user.id != taikhoan.id:
        #     return Response(
        #         {"status": "error", "message": "Bạn không có quyền xem thông tin người dùng này"},
        #         status=status.HTTP_403_FORBIDDEN
        #     )

        serializer = TaiKhoanSerializer(taikhoan)
        user_data = serializer.data
        user_data.pop('nguoidung', None)

        return Response({
            "status": "ok",
            "user": user_data
        }, status=status.HTTP_200_OK)
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = TaiKhoanSerializer(request.user)
        return Response({"status": "ok", "user": serializer.data})
    
class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response(
                {"status": "error", "message": "Email là bắt buộc"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find user with this email
        try:
            nguoidung = NguoiDung.objects.get(email=email)
            taikhoan = nguoidung.fk_taikhoan
        except NguoiDung.DoesNotExist:
            return Response(
                {"status": "error", "message": "Không tìm thấy tài khoản với email này"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate new random password
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        
        # Update user's password
        taikhoan.set_password(new_password)
        taikhoan.save()

        # Send email with new password
        subject = 'Mật khẩu mới của bạn'
        message = f'''
        Xin chào {nguoidung.tennguoidung or 'bạn'},
        
        Chúng tôi nhận được yêu cầu đặt lại mật khẩu của bạn.
        Tên đăng nhập: {taikhoan.tendangnhap}
        Mật khẩu mới: {new_password}
        
        Vui lòng đăng nhập và thay đổi mật khẩu của bạn ngay sau khi đăng nhập.
        
        Trân trọng,
        [Electric store]
        '''
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return Response(
                {"status": "ok", "message": "Mật khẩu mới đã được gửi đến email của bạn"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            # Revert password change if email sending fails
            taikhoan.set_password(password)
            taikhoan.save()
            
            return Response(
                {"status": "error", "message": f"Lỗi gửi email: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class BalanceReductionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Get the total amount to be deducted
        tongtien = request.data.get('tongtien')
        
        # Validate input
        if tongtien is None:
            return Response(
                {"status": "error", "message": "Tổng tiền là bắt buộc"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Convert tongtien to Decimal to match database field type
            tongtien = Decimal(str(tongtien))
        except (ValueError, TypeError, InvalidOperation):
            return Response(
                {"status": "error", "message": "Tổng tiền phải là một số hợp lệ"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if tongtien is positive
        if tongtien <= 0:
            return Response(
                {"status": "error", "message": "Tổng tiền phải là số dương"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the current user's account
        taikhoan = request.user
        
        # Get the associated NguoiDung (user details)
        try:
            nguoidung = taikhoan.nguoidung.first()
            if not nguoidung:
                return Response(
                    {"status": "error", "message": "Không tìm thấy thông tin người dùng"},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {"status": "error", "message": f"Lỗi truy xuất thông tin người dùng: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Check if the user has sufficient balance
        if not nguoidung.sodu or nguoidung.sodu < tongtien:
            return Response(
                {"status": "error", "message": "Số dư không đủ để thực hiện giao dịch"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reduce the balance
        nguoidung.sodu -= tongtien
        nguoidung.save()
        
        return Response({
            "status": "ok", 
            "message": "Trừ tiền thành công", 
            "sodu_moi": str(nguoidung.sodu)  # Convert to string for JSON serialization
        }, status=status.HTTP_200_OK)
    


class BalanceAdditionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sotien = request.data.get('sotien')
        manguoidung = request.data.get('manguoidung')

        if sotien is None:
            return Response(
                {"status": "error", "message": "Số tiền là bắt buộc"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            sotien = Decimal(str(sotien))
        except (ValueError, TypeError, InvalidOperation):
            return Response(
                {"status": "error", "message": "Số tiền phải là một số hợp lệ"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if sotien <= 0:
            return Response(
                {"status": "error", "message": "Số tiền phải là số dương"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not manguoidung:
            return Response(
                {"status": "error", "message": "Mã người dùng là bắt buộc"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Tìm người dùng theo manguoidung
        try:
            nguoidung = NguoiDung.objects.get(pk=manguoidung)
        except NguoiDung.DoesNotExist:
            return Response(
                {"status": "error", "message": "Không tìm thấy người dùng"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": f"Lỗi truy xuất người dùng: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Cộng tiền
        nguoidung.sodu = (nguoidung.sodu or Decimal('0')) + sotien
        nguoidung.save()

        return Response({
            "status": "ok",
            "message": "Nạp tiền thành công",
            "sodu_moi": str(nguoidung.sodu)
        }, status=status.HTTP_200_OK)