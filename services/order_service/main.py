from fastapi import FastAPI
import json
from datetime import datetime

app = FastAPI()
FILE = "orders.json"

@app.post("/orders")
def create_order(order: dict):
    order["timestamp"] = str(datetime.now())

    try:
        with open(FILE, "r") as f:
            data = json.load(f)
    except:
        data = []

    data.append(order)

    with open(FILE, "w") as f:
        json.dump(data, f)

    print("Event: OrderCreated", order)

    return {"message": "Order created"}