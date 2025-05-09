from django.urls import path
from .views import (
    LoginView, UserListView, RegisterView, UserUpdateView, 
    UserDeleteView, UserDetailView, CurrentUserView, 
    PasswordResetView, BalanceReductionView, BalanceAdditionView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('register/', RegisterView.as_view(), name='register'),
    path('users/<int:user_id>/', UserDetailView.as_view(), name='user-detail'),
    path('users/update/<int:user_id>/', UserUpdateView.as_view(), name='user-update'),
    path('users/delete/<int:user_id>/', UserDeleteView.as_view(), name='user-delete'),
    path('auth/me/', CurrentUserView.as_view(), name='current-user'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('balance/reduce/', BalanceReductionView.as_view(), name='balance-reduction'),
    path('balance/add/', BalanceAdditionView.as_view(), name='balance-addition'),
]
