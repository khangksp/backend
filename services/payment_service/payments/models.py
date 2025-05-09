# File: /app/payments/models.py
from django.db import models

class ThanhToan(models.Model):
    pk_MaThanhToan = models.AutoField(primary_key=True)
    fk_MaDonHang = models.IntegerField(unique=True)
    PhuongThucThanhToan = models.CharField(max_length=50, choices=[
        ('cash', 'Cash on Delivery'),
        ('ewallet', 'E-Wallet'),
        ('stripe', 'Stripe')
    ])
    NgayThanhToan = models.DateField()
    TrangThaiThanhToan = models.CharField(max_length=50, choices=[
        ('Chờ thanh toán', 'Chờ thanh toán'),
        ('Đã thanh toán', 'Đã thanh toán'),
        ('Đã hoàn tiền', 'Đã hoàn tiền'),
        ('Thất bại', 'Thất bại')
    ])
    stripe_payment_intent_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'ThanhToan'

class UserBalance(models.Model):
    user_id = models.IntegerField(unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Số dư (VND)

    class Meta:
        db_table = 'UserBalance'