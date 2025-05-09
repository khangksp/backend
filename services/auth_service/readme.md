POST http://localhost:8000/api/auth/login/ 
{
    "username": "testuser1",
    "password": "testpassword123"
}
POST http://localhost:8000/api/auth/register/
{
    "username": "testuser1",
    "email": "123@gmail.com",
    "password": "testpassword123"
}
GET http://localhost:8000/api/auth/users/
response like that 
{
    "status": "ok",
    "users": [
        "admin",
        "testuser1",
        "tai"
    ]
}