from rest_framework import serializers
from django.core.validators import EmailValidator
from .models import TaiKhoan, NguoiDung

class NguoiDungSerializer(serializers.ModelSerializer):
    class Meta:
        model = NguoiDung
        fields = ['manguoidung', 'tennguoidung', 'diachi', 'email', 'sodienthoai', 'sodu']


class TaiKhoanSerializer(serializers.ModelSerializer):
    nguoidung = NguoiDungSerializer(many=False, required=True, write_only=True)
    nguoidung_data = serializers.SerializerMethodField(read_only=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = TaiKhoan
        fields = [
            'mataikhoan', 'tendangnhap', 'password', 'loaiquyen', 'nguoidung', 'nguoidung_data'
        ]
        # extra_kwargs = {
        #     'created_at': {'read_only': True},
        #     'last_login': {'read_only': True},
        #     'is_active': {'read_only': True},
        #     'is_staff': {'read_only': True},
        #     'is_superuser': {'read_only': True},
        # }

    def get_nguoidung_data(self, obj):
        nguoidung = obj.nguoidung.first()
        if nguoidung:
            return NguoiDungSerializer(nguoidung).data
        return None

    def validate_tendangnhap(self, value):
        if not value:
            raise serializers.ValidationError("Tên đăng nhập không được để trống")
        if TaiKhoan.objects.filter(tendangnhap=value).exists():
            raise serializers.ValidationError("Tên đăng nhập này đã được sử dụng")
        return value

    def validate_loaiquyen(self, value):
        valid_roles = ['khach', 'admin', 'nhanvien']
        if value not in valid_roles:
            raise serializers.ValidationError(f"Loại quyền phải là một trong: {valid_roles}")
        return value

    def validate(self, data):
        nguoidung_data = data.get('nguoidung', {})
        email = nguoidung_data.get('email')
        if email and NguoiDung.objects.filter(email=email).exists():
            raise serializers.ValidationError({"nguoidung": {"email": "Email này đã được sử dụng"}})
        return data

    def create(self, validated_data):
        nguoidung_data = validated_data.pop('nguoidung')
        password = validated_data.pop('password', None)
        taikhoan = TaiKhoan(**validated_data)
        if password:
            taikhoan.set_password(password)
        taikhoan.save()
        NguoiDung.objects.create(fk_taikhoan=taikhoan, **nguoidung_data)
        return taikhoan