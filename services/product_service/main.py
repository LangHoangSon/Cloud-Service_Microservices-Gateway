from fastapi import FastAPI

app = FastAPI()

products = [
    {"id": 1, "name": "Laptop", "price": 1000},
    {"id": 2, "name": "Phone", "price": 500}
]

@app.get("/products")
def get_products():
    return products

@app.get("/products/{id}")
def get_product(id: int):
    for p in products:
        if p["id"] == id:
            return p
    return {"error": "Not found"}