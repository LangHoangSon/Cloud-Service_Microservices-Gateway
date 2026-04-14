from fastapi import FastAPI, Request
import httpx

app = FastAPI()

# Service URLs
AUTH_SERVICE = "http://localhost:8001"
PRODUCT_SERVICE = "http://localhost:8002"
ORDER_SERVICE = "http://localhost:8003"

# Simple logger
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"[Gateway] {request.method} {request.url}")
    response = await call_next(request)
    return response


# 🔐 AUTH ROUTE
@app.post("/api/auth/login")
async def login(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{AUTH_SERVICE}/login", json=body)
    return res.json()


# 🛒 PRODUCT ROUTES
@app.get("/api/products")
async def get_products():
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{PRODUCT_SERVICE}/products")
    return res.json()


@app.get("/api/products/{id}")
async def get_product(id: int):
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{PRODUCT_SERVICE}/products/{id}")
    return res.json()


# 📦 ORDER ROUTE
@app.post("/api/orders")
async def create_order(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{ORDER_SERVICE}/orders", json=body)
    return res.json()