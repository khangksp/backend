import requests
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from django.http import JsonResponse

class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'HTTP_AUTHORIZATION' in request.META:
            token = request.META.get('HTTP_AUTHORIZATION').split(' ')[1]
            try:
                # Validate token with Auth service
                response = requests.get(
                    f"{settings.AUTH_SERVICE_URL}/api/auth/users/me/",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    # Token is valid, attach user info to request
                    request.user_data = response.json()
                else:
                    # For simplicity, we'll just continue without user data
                    # In a real application, you might want to enforce authentication
                    request.user_data = None
            except requests.RequestException:
                # Error communicating with Auth service
                # We'll just continue without user data
                request.user_data = None
        else:
            request.user_data = None
            
        response = self.get_response(request)
        return response

def auth_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user_data is None:
            return JsonResponse({"message": "Authentication required"}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper