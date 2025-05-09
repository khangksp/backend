from django.db import models

class TrangThai(models.Model):
    MaTrangThai = models.AutoField(primary_key=True)
    TenTrangThai = models.CharField(max_length=50)
    LoaiTrangThai = models.CharField(max_length=30)
    
    class Meta:
        db_table = 'TrangThai'
    
    def __str__(self):
        return self.TenTrangThai


class DonHang(models.Model):
    MaDonHang = models.AutoField(primary_key=True)
    MaNguoiDung = models.IntegerField()  # Không tạo ForeignKey vì đây là microservice
    NgayDatHang = models.DateTimeField(auto_now_add=True)
    MaTrangThai = models.ForeignKey(TrangThai, on_delete=models.RESTRICT, db_column='MaTrangThai')
    TongTien = models.DecimalField(max_digits=9, decimal_places=0)
    DiaChi = models.TextField()
    
    # Thêm các thông tin về người nhận
    TenNguoiNhan = models.CharField(max_length=100)
    SoDienThoai = models.CharField(max_length=15)
    PhuongThucThanhToan = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'DonHang'


class ChiTietDonHang(models.Model):
    MaChiTietDonHang = models.AutoField(primary_key=True)
    MaDonHang = models.ForeignKey(DonHang, on_delete=models.CASCADE, related_name='chi_tiet', db_column='MaDonHang')
    MaSanPham = models.IntegerField()  # Không tạo ForeignKey vì đây là microservice
    SoLuong = models.IntegerField()
    GiaSanPham = models.DecimalField(max_digits=9, decimal_places=0)
    TenSanPham = models.CharField(max_length=255)
    HinhAnh = models.URLField(null=True, blank=True)
    
    class Meta:
        db_table = 'ChiTietDonHang'