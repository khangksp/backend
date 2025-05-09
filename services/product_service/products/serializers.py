from rest_framework import serializers
from django.conf import settings
from .models import DanhMuc, SanPham, HangSanXuat, ThongSo, ChiTietThongSo

# Thêm cấu hình API Gateway URL (có thể đặt trong settings.py)
API_GATEWAY_URL = getattr(settings, 'API_GATEWAY_URL', 'http://localhost:8000')

class DanhMucSerializer(serializers.ModelSerializer):
    class Meta:
        model = DanhMuc
        fields = ['id', 'TenDanhMuc', 'MoTa', 'NgayTao', 'NgayCapNhat']
        read_only_fields = ['id', 'NgayTao', 'NgayCapNhat']

class HangSanXuatSerializer(serializers.ModelSerializer):
    class Meta:
        model = HangSanXuat
        fields = ['id', 'TenHangSanXuat']

class ThongSoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThongSo
        fields = ['id', 'TenThongSo']

class ChiTietThongSoSerializer(serializers.ModelSerializer):
    TenThongSo = serializers.ReadOnlyField(source='ThongSo.TenThongSo')
    
    class Meta:
        model = ChiTietThongSo
        fields = ['id', 'ThongSo', 'TenThongSo', 'GiaTriThongSo']

class SanPhamSerializer(serializers.ModelSerializer):
    TenDanhMuc = serializers.ReadOnlyField(source='DanhMuc.TenDanhMuc', default=None)
    TenHangSanXuat = serializers.ReadOnlyField(source='HangSanXuat.TenHangSanXuat', default=None)
    ChiTietThongSo = ChiTietThongSoSerializer(source='chi_tiet_thong_so', many=True, read_only=True)
    HinhAnh_URL = serializers.SerializerMethodField()
    
    class Meta:
        model = SanPham
        fields = [
            'id', 'TenSanPham', 'MoTa', 'GiaBan', 'SoLuongTon', 
            'DanhMuc', 'TenDanhMuc', 
            'HangSanXuat', 'TenHangSanXuat',
            'ChiTietThongSo',
            'HinhAnh', 'HinhAnh_URL',
            'NgayTao', 'NgayCapNhat'
        ]
        read_only_fields = ['id', 'NgayTao', 'NgayCapNhat', 'HinhAnh_URL']
        extra_kwargs = {
            'HinhAnh': {'required': False}
        }
    
    def get_HinhAnh_URL(self, obj):
        """
        Trả về URL đầy đủ của hình ảnh thông qua API Gateway
        """
        if obj.HinhAnh:
            # Lấy tên file từ đường dẫn đầy đủ
            image_filename = obj.HinhAnh.name.split('/')[-1]
            # Trả về URL thông qua API Gateway
            return f"{API_GATEWAY_URL}/media/products/{image_filename}"
        return None
    
    def validate_HinhAnh(self, value):
        """
        Kiểm tra file ảnh hợp lệ
        """
        if value:
            # Kiểm tra kích thước file (ví dụ: tối đa 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Kích thước ảnh không được vượt quá 5MB")
            
            # Kiểm tra loại file
            valid_extensions = ['jpg', 'jpeg', 'png', 'webp']
            ext = value.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise serializers.ValidationError(
                    f"Chỉ chấp nhận ảnh có định dạng: {', '.join(valid_extensions)}"
                )
                
        return value

    def create(self, validated_data):
        chi_tiet_thong_so_data = self.context['request'].data.get('ChiTietThongSo', [])
        san_pham = SanPham.objects.create(**validated_data)
        
        # Tạo chi tiết thông số
        for item in chi_tiet_thong_so_data:
            if isinstance(item, dict) and 'ThongSo' in item and 'GiaTriThongSo' in item:
                ChiTietThongSo.objects.create(
                    SanPham=san_pham,
                    ThongSo_id=item['ThongSo'],
                    GiaTriThongSo=item['GiaTriThongSo']
                )
        
        return san_pham
        
    def update(self, instance, validated_data):
        # Cập nhật thông tin sản phẩm
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Cập nhật chi tiết thông số nếu có
        chi_tiet_thong_so_data = self.context['request'].data.get('ChiTietThongSo', [])
        if chi_tiet_thong_so_data:
            # Xóa chi tiết thông số cũ
            instance.chi_tiet_thong_so.all().delete()
            
            # Tạo chi tiết thông số mới
            for item in chi_tiet_thong_so_data:
                if isinstance(item, dict) and 'ThongSo' in item and 'GiaTriThongSo' in item:
                    ChiTietThongSo.objects.create(
                        SanPham=instance,
                        ThongSo_id=item['ThongSo'],
                        GiaTriThongSo=item['GiaTriThongSo']
                    )
        
        return instance