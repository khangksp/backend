from django.db import models
from django.utils.text import slugify
import os
import uuid

def hinh_anh_san_pham_path(instance, filename):
    """Tạo đường dẫn cho hình ảnh sản phẩm"""
    # Tạo tên file với UUID để tránh trùng lặp
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('products', filename)

class HangSanXuat(models.Model):
    TenHangSanXuat = models.CharField(max_length=50)
    
    def __str__(self):
        return self.TenHangSanXuat
    
    class Meta:
        db_table = "HangSanXuat"
        verbose_name = "Hãng Sản Xuất"
        verbose_name_plural = "Hãng Sản Xuất"

class ThongSo(models.Model):
    TenThongSo = models.CharField(max_length=50)
    
    def __str__(self):
        return self.TenThongSo
    
    class Meta:
        db_table = "ThongSo"
        verbose_name = "Thông Số"
        verbose_name_plural = "Thông Số"

class DanhMuc(models.Model):
    TenDanhMuc = models.CharField(max_length=100)
    MoTa = models.TextField(blank=True, null=True)
    NgayTao = models.DateTimeField(auto_now_add=True)
    NgayCapNhat = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.TenDanhMuc
    
    class Meta:
        db_table = "DanhMuc"
        verbose_name = "Danh Mục"
        verbose_name_plural = "Danh Mục"

class SanPham(models.Model):
    TenSanPham = models.CharField(max_length=200)
    MoTa = models.TextField()
    GiaBan = models.DecimalField(max_digits=10, decimal_places=0)
    SoLuongTon = models.PositiveIntegerField(default=0)
    DanhMuc = models.ForeignKey(DanhMuc, related_name='san_pham', on_delete=models.SET_NULL, null=True)
    HangSanXuat = models.ForeignKey(HangSanXuat, on_delete=models.SET_NULL, null=True)
    
    # Thay đổi sang ImageField để lưu ảnh
    HinhAnh = models.ImageField(upload_to=hinh_anh_san_pham_path, blank=True, null=True)
    
    NgayTao = models.DateTimeField(auto_now_add=True)
    NgayCapNhat = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.TenSanPham
    
    class Meta:
        db_table = "SanPham"
        verbose_name = "Sản Phẩm"
        verbose_name_plural = "Sản Phẩm"

class ChiTietThongSo(models.Model):
    SanPham = models.ForeignKey(SanPham, related_name='chi_tiet_thong_so', on_delete=models.CASCADE)
    ThongSo = models.ForeignKey(ThongSo, on_delete=models.CASCADE)
    GiaTriThongSo = models.TextField()
    
    def __str__(self):
        return f"{self.SanPham.TenSanPham} - {self.ThongSo.TenThongSo}: {self.GiaTriThongSo}"
    
    class Meta:
        db_table = "ChiTietThongSo"
        verbose_name = "Chi Tiết Thông Số"
        verbose_name_plural = "Chi Tiết Thông Số"
        unique_together = ('SanPham', 'ThongSo')  # Mỗi sản phẩm chỉ có một giá trị cho mỗi loại thông số