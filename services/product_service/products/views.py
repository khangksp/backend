from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import DanhMuc, SanPham, HangSanXuat, ThongSo, ChiTietThongSo
from .serializers import (
    DanhMucSerializer, SanPhamSerializer,
    HangSanXuatSerializer, ThongSoSerializer, ChiTietThongSoSerializer
)
from .middleware import auth_required
from .rabbitmq import publish_product_event
import os

class DanhMucViewSet(viewsets.ModelViewSet):
    queryset = DanhMuc.objects.all()
    serializer_class = DanhMucSerializer

class HangSanXuatViewSet(viewsets.ModelViewSet):
    queryset = HangSanXuat.objects.all()
    serializer_class = HangSanXuatSerializer

class ThongSoViewSet(viewsets.ModelViewSet):
    queryset = ThongSo.objects.all()
    serializer_class = ThongSoSerializer

class ChiTietThongSoViewSet(viewsets.ModelViewSet):
    queryset = ChiTietThongSo.objects.all()
    serializer_class = ChiTietThongSoSerializer

class SanPhamViewSet(viewsets.ModelViewSet):
    queryset = SanPham.objects.all()
    serializer_class = SanPhamSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def get_queryset(self):
        queryset = SanPham.objects.all()
        
        # Lọc theo danh mục
        danh_muc_id = self.request.query_params.get('danh_muc')
        if danh_muc_id:
            queryset = queryset.filter(DanhMuc_id=danh_muc_id)
        
        # Lọc theo tên
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(TenSanPham__icontains=search)
        
        # Lọc theo khoảng giá
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if min_price:
            queryset = queryset.filter(GiaBan__gte=min_price)
        
        if max_price:
            queryset = queryset.filter(GiaBan__lte=max_price)
        
        # Lọc theo tên
        ten = self.request.query_params.get('ten')
        if ten:
            queryset = queryset.filter(TenSanPham__icontains=ten)
        
        # Lọc theo hãng sản xuất
        hang_san_xuat = self.request.query_params.get('hang_san_xuat')
        if hang_san_xuat:
            queryset = queryset.filter(HangSanXuat_id=hang_san_xuat)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        san_pham = serializer.save()
        
        # Publish sự kiện tạo sản phẩm
        san_pham_data = SanPhamSerializer(san_pham, context={'request': request}).data
        publish_product_event('created', san_pham_data)
        
        headers = self.get_success_headers(serializer.data)
        return Response(san_pham_data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        san_pham = serializer.save()
        
        # Publish sự kiện cập nhật sản phẩm
        san_pham_data = SanPhamSerializer(san_pham, context={'request': request}).data
        publish_product_event('updated', san_pham_data)
        
        return Response(san_pham_data)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        san_pham_data = SanPhamSerializer(instance, context={'request': request}).data
        
        # Xóa file ảnh nếu có
        if instance.HinhAnh:
            if os.path.isfile(instance.HinhAnh.path):
                os.remove(instance.HinhAnh.path)
        
        self.perform_destroy(instance)
        
        # Publish sự kiện xóa sản phẩm
        publish_product_event('deleted', san_pham_data)
        
        return Response(status=status.HTTP_204_NO_CONTENT)