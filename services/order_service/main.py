from fastapi import FastAPI, HTTPException
import json
from datetime import datetime

app = FastAPI()
FILE = "orders.json"

import httpx

PRODUCT_SERVICE = "http://product:8000"

@app.post("/orders/bulk-auto")
async def create_bulk_auto(order: dict):
    if "user" not in order:
        raise HTTPException(status_code=400, detail="Missing user")

    # 🔥 gọi product service
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{PRODUCT_SERVICE}/products")
        products = res.json()

    total_price = sum(p.get("price", 0) for p in products)

    from datetime import datetime
    import json

    new_order = {
        "user": order["user"],
        "products": products,
        "total_price": total_price,
        "timestamp": str(datetime.now())
    }

    try:
        with open("orders.json", "r") as f:
            data = json.load(f)
    except:
        data = []

    data.append(new_order)

    with open("orders.json", "w") as f:
        json.dump(data, f, indent=2)

    return {
        "message": "Bulk order created",
        "total_products": len(products),
        "total_price": total_price
    }