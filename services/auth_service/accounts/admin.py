from django.contrib import admin
from .models import TaiKhoan, NguoiDung

class NguoiDungInline(admin.StackedInline):
    model = NguoiDung
    can_delete = False
    verbose_name_plural = 'Thông tin người dùng'

class TaiKhoanAdmin(admin.ModelAdmin):
    inlines = (NguoiDungInline,)
    list_display = ('tendangnhap', 'loaiquyen', 'is_active', 'last_login')

class NguoiDungAdmin(admin.ModelAdmin):
    list_display = ('tennguoidung', 'email', 'sodienthoai', 'fk_taikhoan')

admin.site.register(TaiKhoan, TaiKhoanAdmin)
admin.site.register(NguoiDung, NguoiDungAdmin)