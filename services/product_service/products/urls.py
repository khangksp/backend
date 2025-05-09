from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DanhMucViewSet, SanPhamViewSet,
    HangSanXuatViewSet, ThongSoViewSet, ChiTietThongSoViewSet
)

router = DefaultRouter()
router.register('danh-muc', DanhMucViewSet, basename='danh-muc')
router.register('hang-san-xuat', HangSanXuatViewSet, basename='hang-san-xuat')
router.register('thong-so', ThongSoViewSet, basename='thong-so')
router.register('chi-tiet-thong-so', ChiTietThongSoViewSet, basename='chi-tiet-thong-so')
router.register('san-pham', SanPhamViewSet, basename='san-pham')

urlpatterns = [
    path('', include(router.urls)),
]