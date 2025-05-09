import jwt
import json
import logging
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)

class JWTAuthentication(BaseAuthentication):
    """
    Custom JWT Authentication for Order Service
    """
    def authenticate(self, request):
        # Lấy token từ header Authorization
        authorization_header = request.headers.get('Authorization', '')
        
        if not authorization_header:
            return None
        
        try:
            # Lấy token từ Authorization header
            if not authorization_header.startswith('Bearer '):
                return None
            
            token = authorization_header.split(' ')[1]
            logger.debug(f"Token found: {token[:10]}...")
            
            # Giải mã token
            try:
                # Thử các secret key khác nhau
                try:
                    # Thử với SECRET_KEY từ settings trước
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                except jwt.InvalidSignatureError:
                    # Nếu không thành công, thử dùng JWT_SECRET_KEY
                    if hasattr(settings, 'JWT_SECRET_KEY'):
                        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
                    else:
                        # Thử dùng SECRET_KEY mặc định của auth_service
                        payload = jwt.decode(
                            token, 
                            "django-insecure-auth-service-key", 
                            algorithms=['HS256']
                        )
            except Exception as e:
                # Thử parse token mà không verify signature (chỉ dùng trong development)
                if settings.DEBUG:
                    header, payload_b64, signature = token.split('.')
                    from base64 import b64decode
                    import json
                    
                    # Decode payload
                    payload_str = b64decode(payload_b64 + '=' * (-len(payload_b64) % 4))
                    payload = json.loads(payload_str)
                    logger.warning(f"Using unverified token payload: {payload}")
                else:
                    raise e
            
            logger.debug(f"Token decoded successfully: {payload}")
            
            # Lấy user_id từ payload - kiểm tra nhiều trường khác nhau
            user_id = None
            possible_id_fields = ['user_id', 'id', 'sub', 'userId']
            
            for field in possible_id_fields:
                if field in payload:
                    user_id = payload[field]
                    break
            
            if not user_id:
                logger.warning("No user_id found in token payload")
                # Sử dụng user_id mặc định nếu không tìm thấy
                user_id = 1  # ID mặc định
            
            # Đảm bảo user_id là số
            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                user_id = 1  # ID mặc định nếu không thể chuyển đổi
            
            # Tạo một đối tượng user custom với thông tin từ token
            user = type('User', (object,), {
                'id': user_id,
                'username': payload.get('username', ''),
                'email': payload.get('email', ''),
                'is_authenticated': True
            })
            
            return (user, token)
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise AuthenticationFailed('Token đã hết hạn')
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            raise AuthenticationFailed('Token không hợp lệ')
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None

class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response