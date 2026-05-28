from faker import Faker

fake = Faker("en_US")
Faker.seed(42)  # Reproducible data across runs

# ── Product catalogue ─────────────────────────────────────────────────────────
CATEGORIES = {
    "Electronics":  [
        ("Laptop Pro 15", 1299.99), ("Wireless Mouse", 29.99), ("Mechanical Keyboard", 129.99),
        ("USB-C Hub", 49.99), ("Monitor 27inch", 399.99), ("Webcam HD", 79.99),
        ("Headphones BT", 149.99), ("Tablet 10inch", 499.99), ("Smartwatch", 249.99),
        ("Portable SSD", 89.99),
    ],
    "Furniture": [
        ("Standing Desk", 499.99), ("Office Chair", 299.99), ("Bookshelf 5-tier", 149.99),
        ("Desk Organizer", 34.99), ("Monitor Stand", 59.99),
    ],
    "Books": [
        ("Python Cookbook", 39.99), ("Clean Code", 44.99), ("Designing Data-Intensive Apps", 49.99),
        ("The Pragmatic Programmer", 42.99), ("Deep Learning", 69.99),
    ],
    "Appliances": [
        ("Coffee Maker", 89.99), ("Desk Lamp LED", 34.99), ("Air Purifier", 199.99),
        ("Electric Kettle", 44.99), ("Mini Fridge", 149.99),
    ],
    "Stationery": [
        ("Notebook Set 3pk", 12.99), ("Whiteboard A1", 49.99), ("Pen Set Premium", 19.99),
        ("Sticky Notes Bulk", 8.99), ("Planner 2025", 24.99),
    ],
}

ORDER_STATUSES        = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
STATUS_WEIGHTS        = [0.05,      0.10,        0.20,      0.58,        0.07]

PAYMENT_METHODS       = ["credit_card", "debit_card", "paypal", "bank_transfer", "crypto"]
PAYMENT_WEIGHTS       = [0.40,          0.25,         0.20,     0.10,            0.05]

CITIES = [
    "Ho Chi Minh City", "Hanoi", "Da Nang", "Can Tho", "Hue",
    "Nha Trang", "Vung Tau", "Bien Hoa", "Thu Duc", "Quy Nhon",
]