from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_cart_view, name='get_cart'),
    path('add/', views.add_to_cart_view, name='add_to_cart'),
    path('update/', views.update_cart_view, name='update_cart'),
    path('remove/<str:product_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('clear/', views.clear_cart_view, name='clear-cart'),
]