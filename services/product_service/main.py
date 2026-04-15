from fastapi import FastAPI

app = FastAPI()

categories = [
    "Electronics",
    "Accessories",
    "Home",
    "Sports",
    "Fashion"
]
brands = [
    "Acme",
    "Nova",
    "Zenith",
    "Pulse",
    "Orion",
    "Vertex",
    "Atlas",
    "Luna"
]

products = []
for i in range(1, 501):
    category = categories[(i - 1) % len(categories)]
    price = 20 + ((i * 17) % 980)
    products.append({
        "id": i,
        "name": f"{category} Item {i}",
        "price": price,
        "category": category,
        "brand": brands[(i - 1) % len(brands)],
        "stock": 5 + ((i * 11) % 95),
        "rating": round(3.0 + ((i * 13) % 20) / 10, 1),
        "description": f"Sample {category.lower()} product number {i}."
    })

@app.get("/products")
def get_products(category: str = None):
    if category:
        return [p for p in products if p["category"] == category]
    return products


@app.get("/products/{id}")
def get_product(id: int):
    for p in products:
        if p["id"] == id:
            return p
    return {"error": "Not found"}