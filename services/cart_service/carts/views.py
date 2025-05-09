from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .utils import (
    get_cart, add_to_cart, update_cart_quantity, 
    remove_from_cart, clear_cart, get_user_id_from_token, merge_carts
)

@api_view(["GET"])
def get_cart_view(request):
    """
    Lấy thông tin giỏ hàng của người dùng hoặc session
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    session_id = request.query_params.get("session_id")

    try:
        user_id = get_user_id_from_token(auth_header)
        if user_id and session_id:
            # Hợp nhất giỏ hàng nếu có cả user_id và session_id
            cart = merge_carts(user_id, session_id)
        else:
            cart = get_cart(user_id=user_id, session_id=session_id)
        return Response(cart)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
def add_to_cart_view(request):
    """
    Thêm sản phẩm vào giỏ hàng
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    data = request.data
    session_id = data.get("session_id")

    try:
        user_id = get_user_id_from_token(auth_header)
        product_id = data.get("product_id")
        if not product_id:
            return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        product_data = {
            "product_id": product_id,
            "name": data.get("name", ""),
            "price": data.get("price", 0),
            "image_url": data.get("image_url", ""),
            "category": data.get("category", ""),
            "selected_color": data.get("selected_color", "default"),
            "size": data.get("size", "Standard"),
        }
        quantity = int(data.get("quantity", 1))

        cart = add_to_cart(user_id=user_id, session_id=session_id, product_data=product_data, quantity=quantity)
        return Response(cart)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["PUT"])
def update_cart_view(request):
    """
    Cập nhật số lượng sản phẩm trong giỏ hàng
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    data = request.data
    session_id = data.get("session_id")

    try:
        user_id = get_user_id_from_token(auth_header)
        product_id = data.get("product_id")
        quantity = int(data.get("quantity", 1))

        if not product_id:
            return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        cart = update_cart_quantity(user_id=user_id, session_id=session_id, product_id=product_id, quantity=quantity)
        return Response(cart)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
def remove_from_cart_view(request, product_id):
    """
    Xóa sản phẩm khỏi giỏ hàng
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    session_id = request.data.get("session_id")

    try:
        user_id = get_user_id_from_token(auth_header)
        cart = remove_from_cart(user_id=user_id, session_id=session_id, product_id=product_id)
        return Response(cart)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
def clear_cart_view(request):
    """
    Xóa toàn bộ giỏ hàng
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    session_id = request.data.get("session_id")

    try:
        user_id = get_user_id_from_token(auth_header)
        cart = clear_cart(user_id=user_id, session_id=session_id)
        return Response(cart)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)