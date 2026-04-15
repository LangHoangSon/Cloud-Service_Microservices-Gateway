from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import jwt
import datetime

app = FastAPI()

SECRET = "secret"

AUTH_SERVICE = "http://auth:8000"
PRODUCT_SERVICE = "http://product:8000"
ORDER_SERVICE = "http://order:8000"

# 🔥 LOG + JWT MIDDLEWARE
@app.middleware("http")
async def middleware(request: Request, call_next):
    print(f"[{datetime.datetime.now()}] {request.method} {request.url}")

    # bỏ qua login và favicon
    if request.url.path not in ["/api/auth/login", "/favicon.ico"]:
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return JSONResponse(status_code=401, content={"detail": "Missing token"})

        token = auth_header
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

        try:
            jwt.decode(token, SECRET, algorithms=["HS256"])
        except jwt.PyJWTError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

    return await call_next(request)

# AUTH
@app.post("/api/auth/login")
async def login(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{AUTH_SERVICE}/login", json=body)
    return res.json()

# PRODUCT
@app.get("/api/products")
async def get_products():
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{PRODUCT_SERVICE}/products")
    return res.json()

# # ORDER
# @app.post("/api/orders")
# async def create_order(request: Request):
#     body = await request.json()
#     async with httpx.AsyncClient() as client:
#         res = await client.post(f"{ORDER_SERVICE}/orders", json=body)
#     return res.json()

@app.post("/api/orders")
async def create_order(request: Request):
    body = await request.json()
    try:
        async with httpx.AsyncClient() as client:
            # Tăng timeout để tránh lỗi khi service khởi động chậm
            res = await client.post(f"{ORDER_SERVICE}/orders", json=body, timeout=10.0)
            
            # Kiểm tra nếu service trả về lỗi (4xx, 5xx)
            res.raise_for_status() 
            
            return res.json()
    except httpx.ConnectError:
        return JSONResponse(status_code=503, content={"detail": "Không thể kết nối đến Order Service. Kiểm tra Docker Network!"})
    except httpx.HTTPStatusError as e:
        # Trả về đúng lỗi mà microservice con đang gặp
        return JSONResponse(status_code=e.response.status_code, content=e.response.text)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    


@app.post("/api/orders/bulk-auto")
async def bulk_order(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{ORDER_SERVICE}/orders/bulk-auto", json=body)
    return res.json()