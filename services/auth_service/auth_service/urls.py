from django.urls import include, path
from django.contrib import admin  # Thêm nếu cần truy cập Django Admin

urlpatterns = [
    path('admin/', admin.site.urls),  # Tùy chọn, nếu bạn muốn dùng Django Admin
    path('api/auth/', include('accounts.urls')),  # Thêm prefix api/auth/
]