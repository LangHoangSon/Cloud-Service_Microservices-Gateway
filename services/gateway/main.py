import os
import httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import jwt
from datetime import datetime

app = FastAPI(
    title="E-Commerce API Gateway",
    description="Single entry point — routes requests to microservices",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Service URLs (injected via docker-compose environment) ──────────────────
SERVICES = {
    "auth":         os.getenv("AUTH_SERVICE_URL",         "http://localhost:8001"),
    "products":     os.getenv("PRODUCT_SERVICE_URL",      "http://localhost:8002"),
    "orders":       os.getenv("ORDER_SERVICE_URL",        "http://localhost:8003"),
    "notifications":os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8004"),
}

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-in-prod")

# Routes that don't require a JWT token
PUBLIC_ROUTES = {
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("GET",  "/health"),
}


# ── JWT validation ───────────────────────────────────────────────────────────
def verify_token(request: Request) -> dict:
    """Extract and validate the Bearer JWT from Authorization header."""
    route_key = (request.method, request.url.path)
    if route_key in PUBLIC_ROUTES:
        return {}

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Generic async proxy helper ───────────────────────────────────────────────
async def proxy(request: Request, target_url: str):
    """Forward any request to target_url, preserve method/headers/body."""
    body = await request.body()

    # Strip hop-by-hop headers before forwarding
    forward_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                content=body,
                params=request.query_params,
            )
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code,
            )
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {target_url}")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Service timeout")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Gateway liveness probe — also pings each downstream service."""
    statuses = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, url in SERVICES.items():
            try:
                r = await client.get(f"{url}/health")
                statuses[name] = "ok" if r.status_code == 200 else f"degraded ({r.status_code})"
            except Exception:
                statuses[name] = "unreachable"

    return {
        "gateway": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": statuses,
    }


# ── Auth routes (/auth/*) ────────────────────────────────────────────────────
@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def auth_proxy(path: str, request: Request, _=Depends(verify_token)):
    target = f"{SERVICES['auth']}/auth/{path}"
    return await proxy(request, target)


# ── Product routes (/products/*) — public GET, auth required for CUD ────────
@app.api_route("/products/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def product_proxy(path: str, request: Request, _=Depends(verify_token)):
    target = f"{SERVICES['products']}/products/{path}"
    return await proxy(request, target)

@app.api_route("/products", methods=["GET"])
async def product_list(request: Request):
    """Public product listing — no auth needed."""
    return await proxy(request, f"{SERVICES['products']}/products")


# ── Order routes (/orders/*) — always requires auth ─────────────────────────
@app.api_route("/orders/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def order_proxy(path: str, request: Request, payload=Depends(verify_token)):
    target = f"{SERVICES['orders']}/orders/{path}"
    return await proxy(request, target)

@app.api_route("/orders", methods=["GET", "POST"])
async def order_root(request: Request, payload=Depends(verify_token)):
    return await proxy(request, f"{SERVICES['orders']}/orders")


# ── Notification routes (/notifications/*) — internal/admin only ─────────────
@app.api_route("/notifications/{path:path}", methods=["GET", "POST"])
async def notification_proxy(path: str, request: Request, _=Depends(verify_token)):
    target = f"{SERVICES['notifications']}/notifications/{path}"
    return await proxy(request, target)
