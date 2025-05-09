from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'all', views.DonHangViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('create/', views.CreateOrderView.as_view(), name='create-order'),
    path('user/<int:user_id>/', views.get_user_orders, name='user-orders'),
    path('user/<int:user_id>/info/', views.get_user_order_info, name='user-order-info'),  # Newly added line
    path('details/<int:order_id>/', views.get_order_details, name='order-details'),
    path('count-orders/', views.count_orders, name='count-orders'),
    path('list-orders/', views.list_orders, name='list-orders'),

    path('update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
]