import json
import jwt
from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed

def get_cart_id(user_id=None, session_id=None):
    """
    Tạo ID giỏ hàng duy nhất cho người dùng hoặc session
    """
    if user_id:
        return f"cart:user:{user_id}"
    if session_id:
        return f"cart:session:{session_id}"
    raise ValueError("Either user_id or session_id must be provided")

def get_cart(user_id=None, session_id=None):
    """
    Lấy giỏ hàng từ Redis dựa trên user_id hoặc session_id
    """
    cart_id = get_cart_id(user_id, session_id)
    cart_data = cache.get(cart_id)
    if cart_data:
        return json.loads(cart_data)
    return {"items": [], "total": 0}

def save_cart(user_id=None, session_id=None, cart_data=None):
    """
    Lưu giỏ hàng vào Redis với thời gian hết hạn
    """
    cart_id = get_cart_id(user_id, session_id)
    cache.set(cart_id, json.dumps(cart_data), timeout=settings.CART_EXPIRY)

def merge_carts(user_id, session_id):
    """
    Hợp nhất giỏ hàng tạm thời (session) với giỏ hàng của người dùng
    """
    session_cart = get_cart(session_id=session_id)
    user_cart = get_cart(user_id=user_id)

    # Hợp nhất các mục
    for session_item in session_cart["items"]:
        existing_item = next(
            (item for item in user_cart["items"] if item["product_id"] == session_item["product_id"]), None
        )
        if existing_item:
            existing_item["quantity"] += session_item["quantity"]
        else:
            user_cart["items"].append(session_item)

    # Cập nhật tổng tiền
    user_cart["total"] = sum(item["price"] * item["quantity"] for item in user_cart["items"])

    # Lưu giỏ hàng người dùng
    save_cart(user_id=user_id, cart_data=user_cart)

    # Xóa giỏ hàng tạm thời
    cache.delete(get_cart_id(session_id=session_id))

    return user_cart

def add_to_cart(user_id=None, session_id=None, product_data=None, quantity=1):
    """
    Thêm sản phẩm vào giỏ hàng
    """
    cart = get_cart(user_id, session_id)
    product_id = product_data.get("product_id")
    existing_item = next((item for item in cart["items"] if item["product_id"] == product_id), None)

    if existing_item:
        existing_item["quantity"] += quantity
    else:
        cart["items"].append({
            "product_id": product_id,
            "name": product_data.get("name", ""),
            "price": float(product_data.get("price", 0)),
            "image_url": product_data.get("image_url", ""),
            "quantity": quantity,
            "category": product_data.get("category", ""),
            "selected_color": product_data.get("selected_color", "default"),
            "size": product_data.get("size", "Standard"),
        })

    cart["total"] = sum(item["price"] * item["quantity"] for item in cart["items"])
    save_cart(user_id, session_id, cart)
    return cart

def update_cart_quantity(user_id=None, session_id=None, product_id=None, quantity=None):
    """
    Cập nhật số lượng sản phẩm trong giỏ hàng
    """
    cart = get_cart(user_id, session_id)
    for item in cart["items"]:
        if item["product_id"] == product_id:
            item["quantity"] = max(1, quantity)
            break

    cart["total"] = sum(item["price"] * item["quantity"] for item in cart["items"])
    save_cart(user_id, session_id, cart)
    return cart

def remove_from_cart(user_id=None, session_id=None, product_id=None):
    """
    Xóa sản phẩm khỏi giỏ hàng
    """
    cart = get_cart(user_id, session_id)
    product_id_str = str(product_id)
    cart["items"] = [item for item in cart["items"] if str(item["product_id"]) != product_id_str]
    cart["total"] = sum(item["price"] * item["quantity"] for item in cart["items"])
    save_cart(user_id, session_id, cart)
    return cart

def clear_cart(user_id=None, session_id=None):
    """
    Xóa toàn bộ giỏ hàng
    """
    cart_id = get_cart_id(user_id, session_id)
    cache.delete(cart_id)
    return {"items": [], "total": 0}

def get_user_id_from_token(token):
    """
    Giải mã JWT token để lấy user_id
    """
    try:
        if not token:
            return None  # Không ném lỗi, chỉ trả về None nếu không có token
        if token.startswith("Bearer "):
            token = token[7:]
        payload = jwt.decode(token, settings.JWT_AUTH["JWT_SECRET_KEY"], algorithms=[settings.JWT_AUTH["JWT_ALGORITHM"]])
        return payload.get("user_id")
    except Exception as e:
        return None