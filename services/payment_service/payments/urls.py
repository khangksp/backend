from django.urls import path
from payments import views

urlpatterns = [
    path('create-checkout-session/', views.create_checkout_session, name='create-checkout-session'),
    path('webhook/', views.stripe_webhook, name='stripe-webhook'),
    path('refund/', views.refund_payment, name='refund-payment'),
]