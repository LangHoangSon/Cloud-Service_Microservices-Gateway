import os
import uuid
import httpx
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from contextlib import asynccontextmanager

from database.database import get_db, init_db
from models.order import Order, OrderItem, OrderStatus

# ── App setup ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()   # Create tables on startup
    yield

app = FastAPI(title="Order Service", version="2.0.0", lifespan=lifespan)

JWT_SECRET       = os.getenv("JWT_SECRET", "super-secret-key-change-in-prod")
JWT_ALGO         = "HS256"
NOTIFICATION_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8004")


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class OrderItemIn(BaseModel):
    product_id: str
    quantity:   int
    unit_price: float

class OrderCreate(BaseModel):
    user_id: str
    items:   list[OrderItemIn]

class StatusUpdate(BaseModel):
    status: str


# ── Auth dependency ───────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer()

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Notification helper ───────────────────────────────────────────────────────
async def _notify(order: Order, event_type: str):
    payload = {
        "user_id":  order.user_id,
        "email":    f"user-{order.user_id[:8]}@example.com",
        "type":     event_type,
        "order_id": order.order_id,
        "message":  f"Your order {order.order_id[:8]} is now {order.status}.",
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{NOTIFICATION_URL}/notifications/send", json=payload)
    except Exception:
        pass  # Never block order on notification failure


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count()).select_from(Order))
    total  = result.scalar()
    return {"service": "order", "status": "ok", "total_orders": total, "storage": "postgresql"}


@app.post("/orders", status_code=201)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth),
):
    if not body.items:
        raise HTTPException(status_code=400, detail="Order must have at least one item")

    total = round(sum(i.quantity * i.unit_price for i in body.items), 2)

    order = Order(
        order_id=str(uuid.uuid4()),
        user_id=body.user_id,
        total_amount=total,
        status=OrderStatus.pending,
    )
    for item in body.items:
        order.items.append(OrderItem(
            item_id=str(uuid.uuid4()),
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
        ))

    db.add(order)
    await db.flush()   # Get order_id before commit
    await db.refresh(order)

    await _notify(order, "order_confirmed")
    return order.to_dict()


@app.get("/orders")
async def list_orders(
    user_id: Optional[str] = Query(None),
    status:  Optional[str] = Query(None),
    limit:   int           = Query(20, ge=1, le=100),
    offset:  int           = Query(0,  ge=0),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth),
):
    query = select(Order).order_by(Order.created_at.desc())

    if user_id:
        query = query.where(Order.user_id == user_id)
    if status:
        if status not in OrderStatus._value2member_map_:
            raise HTTPException(status_code=400, detail=f"Invalid status: {list(OrderStatus._value2member_map_.keys())}")
        query = query.where(Order.status == status)

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Paginated results
    result = await db.execute(query.offset(offset).limit(limit))
    orders = result.scalars().all()

    return {"total": total, "orders": [o.to_dict() for o in orders]}


@app.get("/orders/stats/summary")
async def order_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth),
):
    result = await db.execute(
        select(
            Order.status,
            func.count(Order.order_id).label("count"),
            func.sum(Order.total_amount).label("revenue"),
        ).group_by(Order.status)
    )
    rows = result.all()

    by_status = {r.status: r.count for r in rows}
    total_orders  = sum(r.count   for r in rows)
    total_revenue = sum(r.revenue or 0 for r in rows)

    return {
        "total_orders":    total_orders,
        "total_revenue":   round(total_revenue, 2),
        "avg_order_value": round(total_revenue / total_orders, 2) if total_orders else 0,
        "by_status":       by_status,
        "storage":         "postgresql",
    }


@app.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth),
):
    result = await db.execute(select(Order).where(Order.order_id == order_id))
    order  = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.to_dict()


@app.put("/orders/{order_id}/status")
async def update_status(
    order_id: str,
    body: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth),
):
    if body.status not in OrderStatus._value2member_map_:
        raise HTTPException(status_code=400, detail=f"Invalid status")

    result = await db.execute(select(Order).where(Order.order_id == order_id))
    order  = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status     = body.status
    order.updated_at = datetime.now(timezone.utc)
    await db.flush()

    if body.status in {"confirmed", "shipped", "delivered"}:
        await _notify(order, f"order_{body.status}")

    return order.to_dict()
