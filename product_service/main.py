"""
PRODUCT SERVICE – Port 8002
Endpoints:
  GET /products
  GET /products/<id>
"""

from flask import Flask, jsonify

app = Flask(__name__)

MOCK_PRODUCTS = [
    {"id": 1, "name": "Laptop",  "price": 1000},
    {"id": 2, "name": "Phone",   "price": 500},
    {"id": 3, "name": "Tablet",  "price": 750},
    {"id": 4, "name": "Monitor", "price": 300},
]


@app.route("/products", methods=["GET"])
def get_products():
    return jsonify(MOCK_PRODUCTS), 200


@app.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = next((p for p in MOCK_PRODUCTS if p["id"] == product_id), None)
    if product is None:
        return jsonify({"error": f"Product with id={product_id} not found"}), 404
    return jsonify(product), 200


if __name__ == "__main__":
    print("🛒 Product Service running on http://localhost:8002")
    app.run(port=8002, debug=False)