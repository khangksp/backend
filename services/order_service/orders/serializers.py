from rest_framework import serializers
from .models import TrangThai, DonHang, ChiTietDonHang

class TrangThaiSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrangThai
        fields = '__all__'

class ChiTietDonHangSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChiTietDonHang
        fields = ['MaChiTietDonHang', 'MaSanPham', 'SoLuong', 'GiaSanPham', 'TenSanPham', 'HinhAnh']
        read_only_fields = ['MaChiTietDonHang']

class DonHangSerializer(serializers.ModelSerializer):
    chi_tiet = ChiTietDonHangSerializer(many=True, required=False)
    
    class Meta:
        model = DonHang
        fields = ['MaDonHang', 'MaNguoiDung', 'NgayDatHang', 'MaTrangThai', 'TongTien', 
                 'DiaChi', 'TenNguoiNhan', 'SoDienThoai', 'PhuongThucThanhToan', 'chi_tiet']
        read_only_fields = ['MaDonHang', 'NgayDatHang']
    
    def create(self, validated_data):
        chi_tiet_data = validated_data.pop('chi_tiet', [])
        don_hang = DonHang.objects.create(**validated_data)
        
        for item in chi_tiet_data:
            ChiTietDonHang.objects.create(MaDonHang=don_hang, **item)
            
        return don_hang

class CreateOrderSerializer(serializers.Serializer):
    """Serializer để tạo đơn hàng từ dữ liệu giỏ hàng"""
    user_id = serializers.IntegerField()
    recipient_name = serializers.CharField(max_length=100)
    phone_number = serializers.CharField(max_length=15)
    address = serializers.CharField()
    payment_method = serializers.CharField(max_length=50)
    items = serializers.ListField(child=serializers.JSONField())