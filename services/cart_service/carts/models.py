from django.db import models

# Các mô hình này chỉ dùng để tham khảo, không lưu vào db
class CartItem:
    product_id = None
    name = None
    price = None
    quantity = None
    image_url = None
    category = None
    selected_color = None
    size = None

class Cart:
    user_id = None
    items = []  # Danh sách các CartItem
    total = 0