#!/usr/bin/env python
import os
import json
import time
import requests
import urllib.request
import logging
import sys
from io import BytesIO
from PIL import Image

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL', 'http://api_gateway:8000')
PRODUCT_SERVICE_URL = 'http://product_service:8000'  # Direct service URL
AUTH_SERVICE_URL = 'http://auth_service:8000'  # Auth service URL
MAX_RETRIES = 30  # Number of retries for each request
RETRY_DELAY = 5  # seconds
USE_DIRECT_SERVICE = True  # Set to True to bypass API Gateway

# ======================= AUTH DATA =======================
users = [
    {
        "tendangnhap":"admin123",
        "password": "123456",
        "loaiquyen":"admin",
        "nguoidung":{
            "tennguoidung":"Administrator",
            "diachi":"binh duong",
            "email":"22050006@studenst.bdu.edu.vn",
            "sodienthoai":"012341323"
        }
    },
    {
        "tendangnhap": "nhanvien1",
        "password": "nhanvien123",
        "loaiquyen": "nhanvien",
        "nguoidung": {
            "tennguoidung": "Nhân viên bán hàng",
            "diachi": "Hồ Chí Minh, Việt Nam",
            "email": "nhanvien@example.com",
            "sodienthoai": "0912345678"
        }
    }
]

# ======================= PRODUCT DATA =======================
# Sample data
categories = [
    {"TenDanhMuc": "Điện thoại", "MoTa": "Các loại điện thoại thông minh"},
    {"TenDanhMuc": "Laptop", "MoTa": "Laptop cho công việc và giải trí"},
    {"TenDanhMuc": "Tablet", "MoTa": "Máy tính bảng các loại"},
    {"TenDanhMuc": "Đồng hồ thông minh", "MoTa": "Smartwatch và fitness tracker"},
    {"TenDanhMuc": "Tai nghe", "MoTa": "Tai nghe có dây và không dây"}
]

manufacturers = [
    {"TenHangSanXuat": "Apple"},
    {"TenHangSanXuat": "Samsung"},
    {"TenHangSanXuat": "Xiaomi"},
    {"TenHangSanXuat": "Dell"},
    {"TenHangSanXuat": "Lenovo"},
    {"TenHangSanXuat": "HP"},
    {"TenHangSanXuat": "Asus"},
    {"TenHangSanXuat": "Sony"},
    {"TenHangSanXuat": "Huawei"},
    {"TenHangSanXuat": "Oppo"},
    {"TenHangSanXuat": "MSI"}
]

specifications = [
    {"TenThongSo": "CPU"},
    {"TenThongSo": "RAM"},
    {"TenThongSo": "Bộ nhớ trong"},
    {"TenThongSo": "Màn hình"},
    {"TenThongSo": "Camera sau"},
    {"TenThongSo": "Camera trước"},
    {"TenThongSo": "Pin"},
    {"TenThongSo": "Hệ điều hành"},
    {"TenThongSo": "Card đồ họa"},
    {"TenThongSo": "Kết nối"},
    {"TenThongSo": "Kích thước"},
    {"TenThongSo": "Trọng lượng"}
]

products = [
    {
        "TenSanPham": "iPhone 15 Pro Max",
        "MoTa": "iPhone 15 Pro Max với chip A17 Pro, màn hình Super Retina XDR 6.7 inch và hệ thống camera chuyên nghiệp, thân máy titan ứng dụng công nghệ mới nhất của Apple.",
        "GiaBan": 30990000,
        "SoLuongTon": 50,
        "DanhMuc": 1,  # Điện thoại
        "HangSanXuat": 1,  # Apple
        "HinhAnh_url": "/app/frontend/public/assets/iphone-15-pro-xanh-duong_1694567560.png",
        "ChiTietThongSo": [
            {"ThongSo": 1, "GiaTriThongSo": "A17 Pro 6 nhân"},
            {"ThongSo": 2, "GiaTriThongSo": "8GB"},
            {"ThongSo": 3, "GiaTriThongSo": "512GB"},
            {"ThongSo": 4, "GiaTriThongSo": "6.7 inch, Super Retina XDR, 2796 x 1290 pixel"},
            {"ThongSo": 5, "GiaTriThongSo": "48MP + 12MP + 12MP"},
            {"ThongSo": 6, "GiaTriThongSo": "12MP"},
            {"ThongSo": 7, "GiaTriThongSo": "4422 mAh"},
            {"ThongSo": 8, "GiaTriThongSo": "iOS 17"}
        ]
    },
    {
        "TenSanPham": "Samsung Galaxy S24 Ultra",
        "MoTa": "Samsung Galaxy S24 Ultra với chip Snapdragon 8 Gen 3, màn hình Dynamic AMOLED 2X 6.8 inch và hệ thống camera 200MP, tích hợp S Pen và AI thông minh.",
        "GiaBan": 28990000,
        "SoLuongTon": 40,
        "DanhMuc": 1,  # Điện thoại
        "HangSanXuat": 2,  # Samsung
        "HinhAnh_url": "/app/frontend/public/assets/samsung-galaxy-s24-ultra-cu-1tb.png",
        "ChiTietThongSo": [
            {"ThongSo": 1, "GiaTriThongSo": "Snapdragon 8 Gen 3"},
            {"ThongSo": 2, "GiaTriThongSo": "12GB"},
            {"ThongSo": 3, "GiaTriThongSo": "256GB"},
            {"ThongSo": 4, "GiaTriThongSo": "6.8 inch, Dynamic AMOLED 2X, 3120 x 1440 pixel"},
            {"ThongSo": 5, "GiaTriThongSo": "200MP + 12MP + 10MP + 50MP"},
            {"ThongSo": 6, "GiaTriThongSo": "12MP"},
            {"ThongSo": 7, "GiaTriThongSo": "5000 mAh"},
            {"ThongSo": 8, "GiaTriThongSo": "Android 14, One UI 6.1"}
        ]
    },
    {
        "TenSanPham": "MacBook Pro 16 inch M3 Max",
        "MoTa": "MacBook Pro 16 inch với chip M3 Max mạnh mẽ, màn hình Liquid Retina XDR và thời lượng pin lên đến 22 giờ. Thiết kế sang trọng với khả năng kết nối đa dạng.",
        "GiaBan": 72990000,
        "SoLuongTon": 15,
        "DanhMuc": 2,  # Laptop
        "HangSanXuat": 1,  # Apple
        "HinhAnh_url": "/app/frontend/public/assets/macbook-pro-og-202410.jpg",
        "ChiTietThongSo": [
            {"ThongSo": 1, "GiaTriThongSo": "Apple M3 Max 16 nhân CPU, 40 nhân GPU"},
            {"ThongSo": 2, "GiaTriThongSo": "64GB"},
            {"ThongSo": 3, "GiaTriThongSo": "1TB SSD"},
            {"ThongSo": 4, "GiaTriThongSo": "16.2 inch, Liquid Retina XDR, 3456 x 2234 pixel"},
            {"ThongSo": 7, "GiaTriThongSo": "22 giờ sử dụng"},
            {"ThongSo": 8, "GiaTriThongSo": "macOS Sonoma"},
            {"ThongSo": 9, "GiaTriThongSo": "Apple M3 Max 40 nhân GPU"}
        ]
    },
    {
        "TenSanPham": "MSI Thin GF63",
        "MoTa": "Laptop MSI GF63 với chip Intel Core i5",
        "GiaBan": 19900000,
        "SoLuongTon": 20,
        "DanhMuc": 2,  # Laptop
        "HangSanXuat": 11,  # MSI
        "HinhAnh_url": "/app/frontend/public/assets/text_ng_n_35__8_10_4.png",
        "ChiTietThongSo": [
            {"ThongSo": 1, "GiaTriThongSo": "Intel Core i5-12450H"},
            {"ThongSo": 2, "GiaTriThongSo": "16GB"},
            {"ThongSo": 3, "GiaTriThongSo": "512GB SSD"},
            {"ThongSo": 4, "GiaTriThongSo": "15.6 inch, IPS, Full HD"},
            {"ThongSo": 7, "GiaTriThongSo": "51Wh"},
            {"ThongSo": 8, "GiaTriThongSo": "Windows 11"},
            {"ThongSo": 9, "GiaTriThongSo": "NVIDIA GeForce RTX 3050 4GB"}
        ]
    }
]

# Image placeholders for when fetching real images fails
image_placeholders = {
    1: "https://via.placeholder.com/600x600.png?text=Smartphone",
    2: "https://via.placeholder.com/600x600.png?text=Laptop",
    3: "https://via.placeholder.com/600x600.png?text=Tablet",
    4: "https://via.placeholder.com/600x600.png?text=Smartwatch",
    5: "https://via.placeholder.com/600x600.png?text=Headphones"
}


def check_service(service_name, url, path=""):
    """Check if a service is available"""
    check_url = f"{url}{path}"
    logger.info(f"Checking if {service_name} is available at {check_url}")
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(check_url, timeout=10, headers={'Host': 'localhost'})
            logger.info(f"Response from {service_name}: {response.status_code}")
            
            if response.status_code < 500:  # Accept any non-server error response
                logger.info(f"{service_name} is available!")
                return True
        except requests.RequestException as e:
            logger.warning(f"Cannot connect to {service_name} (attempt {attempt+1}/{MAX_RETRIES}): {e}")
        
        logger.info(f"Retrying {service_name} in {RETRY_DELAY} seconds...")
        time.sleep(RETRY_DELAY)
    
    logger.error(f"Failed to connect to {service_name} after {MAX_RETRIES} attempts")
    return False


def wait_for_services():
    """Wait for all required services to be available"""
    services_to_check = [
        ("API Gateway", API_GATEWAY_URL, "/health"),
        ("Product Service", PRODUCT_SERVICE_URL, "/api/products/"),
        ("Auth Service", AUTH_SERVICE_URL, "/api/auth/users/")
    ]
    
    all_available = True
    for name, url, path in services_to_check:
        if not check_service(name, url, path):
            all_available = False
    
    return all_available


def download_and_process_image(image_source, category_id):
    """Download and process an image, returning the file object"""
    try:
        # Check if the source is a URL or local file path
        if image_source.startswith(('http://', 'https://')):
            # Handle as URL
            logger.info(f"Downloading image from URL: {image_source}")
            response = urllib.request.urlopen(image_source, timeout=10)
            image_data = response.read()
            image = Image.open(BytesIO(image_data))
        else:
            # Handle as local file
            logger.info(f"Opening local image: {image_source}")
            if os.path.exists(image_source):
                image = Image.open(image_source)
            else:
                logger.error(f"Local file not found: {image_source}")
                return None
        
        # Process image (resize, convert, etc)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large
        max_size = 1200
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size))
        
        # Save to memory buffer
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        
        logger.info(f"Image processed successfully")
        return buffer
    
    except Exception as e:
        logger.error(f"Error processing image {image_source}: {e}")
        # Try placeholder as fallback
        try:
            placeholder_url = image_placeholders.get(category_id, "https://via.placeholder.com/600x600.png?text=Product")
            logger.info(f"Using placeholder image: {placeholder_url}")
            response = urllib.request.urlopen(placeholder_url, timeout=10)
            return BytesIO(response.read())
        except Exception as e2:
            logger.error(f"Error with placeholder image too: {e2}")
            return None


def make_api_request(method, endpoint, base_url=None, **kwargs):
    """Make API request with retries and detailed logging"""
    if base_url is None:
        if endpoint.startswith('/api/auth/'):
            base_url = AUTH_SERVICE_URL if USE_DIRECT_SERVICE else API_GATEWAY_URL
        else:
            base_url = PRODUCT_SERVICE_URL if USE_DIRECT_SERVICE else API_GATEWAY_URL
    
    url = f"{base_url}{endpoint}"
    logger.info(f"Making {method} request to {url}")
    
    # Add default headers if not provided
    headers = kwargs.get('headers', {})
    if 'Accept' not in headers:
        headers['Accept'] = 'application/json'
    headers['Host'] = 'localhost'
    
    kwargs['headers'] = headers
    
    # Log request body if present
    if 'json' in kwargs:
        logger.info(f"Request body (json): {kwargs['json']}")
    elif 'data' in kwargs and not kwargs.get('files'):
        logger.info(f"Request body (data): {kwargs['data']}")
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.request(method, url, **kwargs)
            logger.info(f"Response status: {response.status_code}")
            if response.text:
                logger.info(f"Response content: {response.text[:500]}...")  # First 500 chars
            
            if response.status_code in (200, 201):
                return response
            
            logger.warning(f"Request failed with status {response.status_code}")
            
            # For client errors (4xx), no need to retry
            if 400 <= response.status_code < 500:
                return response
            
        except requests.RequestException as e:
            logger.error(f"Request exception: {e}")
        
        logger.info(f"Retrying request in {RETRY_DELAY} seconds (attempt {attempt+1}/{MAX_RETRIES})...")
        time.sleep(RETRY_DELAY)
    
    logger.error(f"Failed to get successful response after {MAX_RETRIES} attempts")
    return None


# ======================= AUTH FUNCTIONS =======================
def seed_users():
    """Create admin and employee users"""
    logger.info("Creating users...")
    created_users = []
    
    for user in users:
        logger.info(f"Creating user: {user['tendangnhap']} with role {user['loaiquyen']}")
        
        # Check if user already exists by trying to login
        login_data = {
            "tendangnhap": user["tendangnhap"],
            "password": user["password"]
        }
        
        login_response = make_api_request('POST', '/api/auth/login/', json=login_data)
        
        if login_response and login_response.status_code == 200:
            logger.info(f"User {user['tendangnhap']} already exists. Skipping creation.")
            created_users.append(user['tendangnhap'])
            continue
        
        # Register new user
        response = make_api_request('POST', '/api/auth/register/', json=user)
        
        if response and response.status_code == 201:
            logger.info(f"Successfully created user: {user['tendangnhap']} with role {user['loaiquyen']}")
            created_users.append(user['tendangnhap'])
        else:
            logger.error(f"Failed to create user: {user['tendangnhap']}")
    
    return created_users


# ======================= PRODUCT FUNCTIONS =======================
def seed_categories():
    """Seed categories with detailed error handling"""
    logger.info("Creating categories...")
    category_mapping = {}
    
    for category in categories:
        try:
            # Try both with json and data parameters
            for param_type in ['json', 'data']:
                kwargs = {param_type: category}
                response = make_api_request('POST', '/api/products/danh-muc/', **kwargs)
                
                if response and response.status_code in (200, 201):
                    category_data = response.json()
                    category_id = category_data.get('id')
                    category_mapping[category_data.get('TenDanhMuc')] = category_id
                    logger.info(f"Created category: {category_data.get('TenDanhMuc')} (ID: {category_id})")
                    break
                
                logger.warning(f"Failed with {param_type} parameter, trying alternative...")
            
            # If we got here without a break, both attempts failed
            else:
                logger.error(f"All attempts to create category {category['TenDanhMuc']} failed")
        
        except Exception as e:
            logger.error(f"Error creating category {category['TenDanhMuc']}: {e}")
    
    # Return the IDs we were able to create
    return category_mapping


def seed_manufacturers():
    """Seed manufacturers with detailed error handling"""
    logger.info("Creating manufacturers...")
    manufacturer_mapping = {}
    
    for manufacturer in manufacturers:
        try:
            # Try both with json and data parameters
            for param_type in ['json', 'data']:
                kwargs = {param_type: manufacturer}
                response = make_api_request('POST', '/api/products/hang-san-xuat/', **kwargs)
                
                if response and response.status_code in (200, 201):
                    manufacturer_data = response.json()
                    manufacturer_id = manufacturer_data.get('id')
                    manufacturer_mapping[manufacturer_data.get('TenHangSanXuat')] = manufacturer_id
                    logger.info(f"Created manufacturer: {manufacturer_data.get('TenHangSanXuat')} (ID: {manufacturer_id})")
                    break
                
                logger.warning(f"Failed with {param_type} parameter, trying alternative...")
            
            # If we got here without a break, both attempts failed
            else:
                logger.error(f"All attempts to create manufacturer {manufacturer['TenHangSanXuat']} failed")
        
        except Exception as e:
            logger.error(f"Error creating manufacturer {manufacturer['TenHangSanXuat']}: {e}")
    
    # Return the IDs we were able to create
    return manufacturer_mapping


def seed_specifications():
    """Seed specifications with detailed error handling"""
    logger.info("Creating specifications...")
    spec_mapping = {}
    
    for spec in specifications:
        try:
            # Try both with json and data parameters
            for param_type in ['json', 'data']:
                kwargs = {param_type: spec}
                response = make_api_request('POST', '/api/products/thong-so/', **kwargs)
                
                if response and response.status_code in (200, 201):
                    spec_data = response.json()
                    spec_id = spec_data.get('id')
                    spec_mapping[spec_data.get('TenThongSo')] = spec_id
                    logger.info(f"Created specification: {spec_data.get('TenThongSo')} (ID: {spec_id})")
                    break
                
                logger.warning(f"Failed with {param_type} parameter, trying alternative...")
            
            # If we got here without a break, both attempts failed
            else:
                logger.error(f"All attempts to create specification {spec['TenThongSo']} failed")
        
        except Exception as e:
            logger.error(f"Error creating specification {spec['TenThongSo']}: {e}")
    
    # Return the IDs we were able to create
    return spec_mapping


def seed_products(use_placeholder=False):
    """Seed products with detailed error handling"""
    logger.info("Creating products...")
    product_count = 0
    
    for product in products:
        try:
            # Download image or use placeholder
            image_file = None
            if use_placeholder:
                placeholder_url = image_placeholders.get(product['DanhMuc'], "https://via.placeholder.com/600x600.png?text=Product")
                logger.info(f"Using placeholder image for {product['TenSanPham']}: {placeholder_url}")
                try:
                    response = urllib.request.urlopen(placeholder_url, timeout=10)
                    image_file = BytesIO(response.read())
                except Exception as e:
                    logger.error(f"Error with placeholder image: {e}")
            else:
                image_file = download_and_process_image(product['HinhAnh_url'], product['DanhMuc'])
            
            # Create form data for multipart request
            form_data = {
                'TenSanPham': product['TenSanPham'],
                'MoTa': product['MoTa'],
                'GiaBan': str(product['GiaBan']),
                'SoLuongTon': str(product['SoLuongTon']),
                'DanhMuc': str(product['DanhMuc']),
                'HangSanXuat': str(product['HangSanXuat']),
                'ChiTietThongSo': json.dumps(product['ChiTietThongSo'])
            }
            
            logger.info(f"Form data prepared for {product['TenSanPham']}: {form_data}")
            
            files = {}
            if image_file:
                files = {
                    'HinhAnh': ('product_image.jpg', image_file, 'image/jpeg')
                }
                logger.info("Image file attached")
            
            # Try creating the product
            response = make_api_request('POST', '/api/products/san-pham/', data=form_data, files=files)
            
            if response and response.status_code in (200, 201):
                product_data = response.json()
                logger.info(f"Created product: {product_data.get('TenSanPham')} (ID: {product_data.get('id')})")
                product_count += 1
            else:
                logger.error(f"Failed to create product {product['TenSanPham']}")
                
                # Try alternative method without image
                logger.info("Trying without image...")
                response = make_api_request('POST', '/api/products/san-pham/', json={
                    'TenSanPham': product['TenSanPham'],
                    'MoTa': product['MoTa'],
                    'GiaBan': product['GiaBan'],
                    'SoLuongTon': product['SoLuongTon'],
                    'DanhMuc': product['DanhMuc'],
                    'HangSanXuat': product['HangSanXuat'],
                    'ChiTietThongSo': product['ChiTietThongSo']
                })
                
                if response and response.status_code in (200, 201):
                    product_data = response.json()
                    logger.info(f"Created product (alternative method): {product_data.get('TenSanPham')} (ID: {product_data.get('id')})")
                    product_count += 1
            
        except Exception as e:
            logger.error(f"Error creating product {product['TenSanPham']}: {e}")
    
    return product_count


def test_api_endpoints():
    """Test API endpoints to see which ones are working"""
    logger.info("Testing API endpoints...")
    
    endpoints = [
        ('/api/products/', 'GET'),
        ('/api/products/danh-muc/', 'GET'),
        ('/api/products/hang-san-xuat/', 'GET'),
        ('/api/products/thong-so/', 'GET'),
        ('/api/products/san-pham/', 'GET'),
        ('/api/auth/users/', 'GET'),
    ]
    
    # Try both direct and via API Gateway
    for base in [PRODUCT_SERVICE_URL, API_GATEWAY_URL]:
        logger.info(f"Testing with base URL: {base}")
        
        for endpoint, method in endpoints:
            # Skip auth endpoints when testing product service directly
            if base == PRODUCT_SERVICE_URL and endpoint.startswith('/api/auth/'):
                continue
                
            url = f"{base}{endpoint}"
            try:
                response = requests.request(method, url, timeout=5, headers={'Host': 'localhost'})
                logger.info(f"{method} {url} - Status: {response.status_code}")
                if len(response.text) < 1000:
                    logger.info(f"Response: {response.text}")
                else:
                    logger.info(f"Response (truncated): {response.text[:500]}...")
            except Exception as e:
                logger.error(f"Error testing {url}: {e}")


def check_django_urls():
    """Try to access the Django admin to verify Django is running properly"""
    try:
        response = requests.get(f"{PRODUCT_SERVICE_URL}/admin/login/", timeout=5, headers={'Host': 'localhost'})
        logger.info(f"Django admin response: {response.status_code}")
        if response.status_code == 200:
            logger.info("Django admin is accessible, which confirms Django is running")
        else:
            logger.warning("Django admin returned non-200 status code")
    except Exception as e:
        logger.error(f"Error accessing Django admin: {e}")


def seed_data():
    """Seed the database with initial data with comprehensive error handling"""
    logger.info("========== TESTING API ENDPOINTS ==========")
    # First test the API endpoints
    test_api_endpoints()
    
    # Check Django is running
    check_django_urls()
    
    logger.info("========== CREATING USERS ==========")
    # Seed users first
    created_users = seed_users()
    if created_users:
        logger.info(f"Successfully created users: {', '.join(created_users)}")
    else:
        logger.warning("No new users were created.")
    
    logger.info("========== CREATING PRODUCT DATA ==========")
    # Seed categories
    category_mapping = seed_categories()
    if not category_mapping:
        logger.error("Failed to create any categories. Aborting product creation.")
        return False
    
    # Add a delay between operations
    logger.info("Waiting for categories to be fully processed...")
    time.sleep(5)
    
    # Seed manufacturers
    manufacturer_mapping = seed_manufacturers()
    if not manufacturer_mapping:
        logger.error("Failed to create any manufacturers. Aborting product creation.")
        return False
    
    # Add a delay between operations
    logger.info("Waiting for manufacturers to be fully processed...")
    time.sleep(5)
    
    # Seed specifications
    spec_mapping = seed_specifications()
    if not spec_mapping:
        logger.error("Failed to create any specifications. Aborting product creation.")
        return False
    
    # Add a delay between operations
    logger.info("Waiting for specifications to be fully processed...")
    time.sleep(5)
    
    # Seed products
    product_count = seed_products(use_placeholder=False)  # Use actual image files
    logger.info(f"Created {product_count} products")
    
    return True


if __name__ == '__main__':
    logger.info("Starting seed.py script...")
    logger.info(f"API Gateway URL: {API_GATEWAY_URL}")
    logger.info(f"Product Service URL: {PRODUCT_SERVICE_URL}")
    logger.info(f"Auth Service URL: {AUTH_SERVICE_URL}")
    logger.info(f"Direct service mode: {USE_DIRECT_SERVICE}")
    
    if wait_for_services():
        logger.info("All services are available. Starting data seeding process...")
        if seed_data():
            logger.info("Data seeding completed successfully!")
        else:
            logger.error("Data seeding failed or was incomplete.")
    else:
        logger.error("Services are not available. Exiting without seeding data.")