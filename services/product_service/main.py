import os
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI(title="Product Service", version="1.0.0")

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-in-prod")
JWT_ALGO   = "HS256"

PRODUCTS_FILE = Path("products.json")

# ── File store helpers ────────────────────────────────────────────────────────
def _load() -> dict:
    if not PRODUCTS_FILE.exists():
        # Seed with some sample products on first run
        sample = _seed_products()
        PRODUCTS_FILE.write_text(json.dumps(sample, indent=2))
        return sample
    return json.loads(PRODUCTS_FILE.read_text())

def _save(products: dict):
    PRODUCTS_FILE.write_text(json.dumps(products, indent=2))

def _seed_products() -> dict:
    """Generate 10 sample products so the service works out of the box."""
    now = datetime.now(timezone.utc).isoformat()
    items = [
        ("Laptop Pro 15",      "Electronics", 1299.99, 50,  "High-performance laptop"),
        ("Wireless Mouse",     "Electronics",   29.99, 200, "Ergonomic wireless mouse"),
        ("Standing Desk",      "Furniture",    499.99,  30, "Height-adjustable desk"),
        ("Python Cookbook",    "Books",         39.99, 150, "Advanced Python recipes"),
        ("Coffee Maker",       "Appliances",    89.99,  75, "12-cup programmable"),
        ("Mechanical Keyboard","Electronics",  129.99,  80, "RGB mechanical keyboard"),
        ("Office Chair",       "Furniture",    299.99,  40, "Ergonomic mesh chair"),
        ("USB-C Hub",          "Electronics",   49.99, 120, "7-in-1 USB-C hub"),
        ("Notebook Set",       "Stationery",    12.99, 300, "Pack of 3 notebooks"),
        ("Desk Lamp",          "Appliances",    34.99, 100, "LED adjustable lamp"),
    ]
    products = {}
    for name, category, price, stock, desc in items:
        pid = str(uuid.uuid4())
        products[pid] = {
            "product_id":  pid,
            "name":        name,
            "description": desc,
            "category":    category,
            "price":       price,
            "stock":       stock,
            "created_at":  now,
            "updated_at":  now,
        }
    return products


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class ProductCreate(BaseModel):
    name: str
    description: str = ""
    category: str
    price: float
    stock: int = 0

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None

class ProductResponse(BaseModel):
    product_id: str
    name: str
    description: str
    category: str
    price: float
    stock: int
    created_at: str
    updated_at: str

class ProductListResponse(BaseModel):
    total: int
    products: list[ProductResponse]


# ── Auth dependency ───────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer()

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"service": "product", "status": "ok"}


@app.get("/products", response_model=ProductListResponse)
def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    search:   Optional[str] = Query(None, description="Search by name"),
    min_price:Optional[float]= Query(None, ge=0),
    max_price:Optional[float]= Query(None, ge=0),
    limit:    int            = Query(20, ge=1, le=100),
    offset:   int            = Query(0,  ge=0),
):
    products = list(_load().values())

    if category:
        products = [p for p in products if p["category"].lower() == category.lower()]
    if search:
        products = [p for p in products if search.lower() in p["name"].lower()]
    if min_price is not None:
        products = [p for p in products if p["price"] >= min_price]
    if max_price is not None:
        products = [p for p in products if p["price"] <= max_price]

    total = len(products)
    page  = products[offset: offset + limit]

    return ProductListResponse(total=total, products=page)


@app.get("/products/categories")
def list_categories():
    """Return all distinct categories."""
    products = _load()
    cats = sorted(set(p["category"] for p in products.values()))
    return {"categories": cats}


@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: str):
    products = _load()
    product = products.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.post("/products", response_model=ProductResponse, status_code=201)
def create_product(body: ProductCreate, _=Depends(require_auth)):
    products = _load()
    now = datetime.now(timezone.utc).isoformat()
    pid = str(uuid.uuid4())

    product = {
        "product_id":  pid,
        "name":        body.name,
        "description": body.description,
        "category":    body.category,
        "price":       body.price,
        "stock":       body.stock,
        "created_at":  now,
        "updated_at":  now,
    }
    products[pid] = product
    _save(products)
    return product


@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: str, body: ProductUpdate, _=Depends(require_auth)):
    products = _load()
    product = products.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Only update fields that were actually sent
    updates = body.model_dump(exclude_none=True)
    product.update(updates)
    product["updated_at"] = datetime.now(timezone.utc).isoformat()

    products[product_id] = product
    _save(products)
    return product


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: str, _=Depends(require_auth)):
    products = _load()
    if product_id not in products:
        raise HTTPException(status_code=404, detail="Product not found")
    del products[product_id]
    _save(products)


@app.patch("/products/{product_id}/stock")
def update_stock(product_id: str, delta: int, _=Depends(require_auth)):
    """Increment or decrement stock. Pass negative delta to decrease."""
    products = _load()
    product = products.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    new_stock = product["stock"] + delta
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    product["stock"] = new_stock
    product["updated_at"] = datetime.now(timezone.utc).isoformat()
    products[product_id] = product
    _save(products)
    return {"product_id": product_id, "stock": new_stock}
