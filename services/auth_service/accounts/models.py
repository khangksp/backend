from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

class TaiKhoanManager(BaseUserManager):
    def create_user(self, tendangnhap, password=None, **extra_fields):
        if not tendangnhap:
            raise ValueError('Trường Tên đăng nhập không được để trống')
        user = self.model(tendangnhap=tendangnhap, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, tendangnhap, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('loaiquyen', 'admin')
        return self.create_user(tendangnhap, password, **extra_fields)

class TaiKhoan(AbstractBaseUser):
    LOAIQUYEN_CHOICES = (
        ('admin', 'Admin'),
        ('nhanvien', 'Nhân viên'),
        ('khach', 'Khách'),
    )

    mataikhoan = models.AutoField(primary_key=True)
    tendangnhap = models.CharField(max_length=255, unique=True)
    matkhau = models.CharField(max_length=255)
    loaiquyen = models.CharField(max_length=20, choices=LOAIQUYEN_CHOICES, default='khach')
    created_at = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = TaiKhoanManager()

    USERNAME_FIELD = 'tendangnhap'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'taikhoan'
        managed = False

    def set_password(self, raw_password):
        self.matkhau = make_password(raw_password)
        self._password = raw_password

    def check_password(self, raw_password):
        return check_password(raw_password, self.matkhau)

    @property
    def password(self):
        return self.matkhau

    @password.setter
    def password(self, value):
        self.matkhau = value

class NguoiDung(models.Model):
    manguoidung = models.AutoField(primary_key=True)
    tennguoidung = models.CharField(max_length=255)
    diachi = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True)
    sodienthoai = models.CharField(max_length=255, unique=True)
    sodu = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)  # Thêm dòng này
    fk_taikhoan = models.ForeignKey(
        TaiKhoan,
        on_delete=models.CASCADE,
        related_name='nguoidung',
        db_column='fk_taikhoan' 
    )

    class Meta:
        db_table = 'nguoidung'
        managed = False
