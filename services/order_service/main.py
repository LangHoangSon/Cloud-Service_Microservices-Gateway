import os
import uuid
import json
import httpx
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI(title="Order Service", version="1.0.0")

JWT_SECRET            = os.getenv("JWT_SECRET", "super-secret-key-change-in-prod")
JWT_ALGO              = "HS256"
NOTIFICATION_URL      = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8004")
ORDERS_DIR            = Path("orders")
ORDERS_FILE           = ORDERS_DIR / "orders.json"

ORDERS_DIR.mkdir(exist_ok=True)

ORDER_STATUSES = {"pending", "confirmed", "shipped", "delivered", "cancelled"}


# ── File store ────────────────────────────────────────────────────────────────
def _load() -> dict:
    if not ORDERS_FILE.exists():
        ORDERS_FILE.write_text("{}")
    return json.loads(ORDERS_FILE.read_text())

def _save(orders: dict):
    ORDERS_FILE.write_text(json.dumps(orders, indent=2, ensure_ascii=False))


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class OrderItem(BaseModel):
    product_id: str
    quantity:   int
    unit_price: float

class OrderCreate(BaseModel):
    user_id: str
    items:   list[OrderItem]

class StatusUpdate(BaseModel):
    status: str

class OrderResponse(BaseModel):
    order_id:     str
    user_id:      str
    status:       str
    total_amount: float
    items:        list[dict]
    created_at:   str
    updated_at:   str

class OrderListResponse(BaseModel):
    total:  int
    orders: list[OrderResponse]


# ── Auth dependency ───────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer()

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Notification helper (fire-and-forget) ─────────────────────────────────────
async def _notify(order: dict, event_type: str):
    """Send notification asynchronously — failure never blocks the order response."""
    payload = {
        "user_id":  order["user_id"],
        "email":    f"user-{order['user_id'][:8]}@example.com",
        "type":     event_type,
        "order_id": order["order_id"],
        "message":  f"Your order {order['order_id'][:8]} is now {order['status']}.",
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{NOTIFICATION_URL}/notifications/send", json=payload)
    except Exception:
        pass  # Notification failure must never fail the order


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    orders = _load()
    return {"service": "order", "status": "ok", "total_orders": len(orders)}


@app.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(body: OrderCreate, _=Depends(require_auth)):
    if not body.items:
        raise HTTPException(status_code=400, detail="Order must have at least one item")

    orders  = _load()
    now     = datetime.now(timezone.utc).isoformat()
    oid     = str(uuid.uuid4())
    total   = sum(item.quantity * item.unit_price for item in body.items)

    order = {
        "order_id":     oid,
        "user_id":      body.user_id,
        "status":       "pending",
        "total_amount": round(total, 2),
        "items":        [i.model_dump() for i in body.items],
        "created_at":   now,
        "updated_at":   now,
    }
    orders[oid] = order
    _save(orders)

    await _notify(order, "order_confirmed")
    return order


@app.get("/orders", response_model=OrderListResponse)
def list_orders(
    user_id: Optional[str] = Query(None),
    status:  Optional[str] = Query(None),
    limit:   int           = Query(20, ge=1, le=100),
    offset:  int           = Query(0,  ge=0),
    _=Depends(require_auth),
):
    orders = list(_load().values())

    if user_id:
        orders = [o for o in orders if o["user_id"] == user_id]
    if status:
        if status not in ORDER_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Use: {ORDER_STATUSES}")
        orders = [o for o in orders if o["status"] == status]

    # Sort newest first
    orders.sort(key=lambda o: o["created_at"], reverse=True)

    total = len(orders)
    return OrderListResponse(total=total, orders=orders[offset: offset + limit])


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, _=Depends(require_auth)):
    orders = _load()
    order  = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.put("/orders/{order_id}/status", response_model=OrderResponse)
async def update_status(order_id: str, body: StatusUpdate, _=Depends(require_auth)):
    if body.status not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {ORDER_STATUSES}")

    orders = _load()
    order  = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order["status"]     = body.status
    order["updated_at"] = datetime.now(timezone.utc).isoformat()
    orders[order_id]    = order
    _save(orders)

    # Notify on meaningful status transitions
    if body.status in {"confirmed", "shipped", "delivered"}:
        await _notify(order, f"order_{body.status}")

    return order


@app.get("/orders/stats/summary")
def order_stats(_=Depends(require_auth)):
    """Quick summary stats — useful for dashboard and Databricks validation."""
    orders = list(_load().values())
    if not orders:
        return {"total": 0}

    by_status = {}
    for o in orders:
        by_status[o["status"]] = by_status.get(o["status"], 0) + 1

    total_revenue = sum(o["total_amount"] for o in orders)

    return {
        "total_orders":   len(orders),
        "total_revenue":  round(total_revenue, 2),
        "by_status":      by_status,
        "avg_order_value": round(total_revenue / len(orders), 2),
    }