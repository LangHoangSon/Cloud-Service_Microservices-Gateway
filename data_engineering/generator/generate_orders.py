"""
Generate 5 million synthetic e-commerce orders with realistic patterns.

Features:
  - VIP users order more frequently and spend more
  - Seasonal peaks (Nov-Dec, Feb for Valentine's, 6.6 / 11.11 sale days)
  - Multi-item orders (1–5 items, weighted)
  - Realistic timestamps spread over 2 years
  - Outputs chunked JSON files (500k orders each) → easier DBFS upload

Usage:
    python generate_orders.py --orders 5000000 --users-file ../raw_data/users/users.json
"""
import uuid
import json
import random
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from itertools import islice

from faker_config import (
    fake, CATEGORIES, ORDER_STATUSES, STATUS_WEIGHTS,
    PAYMENT_METHODS, PAYMENT_WEIGHTS,
)

# Flatten product catalogue into a list for random selection
ALL_PRODUCTS = []
for category, items in CATEGORIES.items():
    for name, price in items:
        ALL_PRODUCTS.append({
            "product_id": str(uuid.uuid4()),
            "name":       name,
            "category":   category,
            "price":      price,
        })


def _seasonal_weight(dt: datetime) -> float:
    """Return a multiplier based on month — simulates sales seasonality."""
    month = dt.month
    day   = dt.day
    # Nov-Dec holiday season
    if month in (11, 12):
        return 2.5
    # 11.11 singles day
    if month == 11 and day == 11:
        return 5.0
    # 6.6 mid-year sale
    if month == 6 and day == 6:
        return 3.0
    # Valentine's
    if month == 2 and day in range(10, 15):
        return 1.8
    # Summer dip
    if month in (7, 8):
        return 0.7
    return 1.0


def _random_timestamp(segment: str) -> datetime:
    """
    VIP and regular users have orders distributed over 2 years.
    Occasional users cluster in the last 6 months.
    New users only in the last 30 days.
    """
    now = datetime.now(timezone.utc)
    if segment == "vip":
        days = random.randint(0, 730)
    elif segment == "regular":
        days = random.randint(0, 730)
    elif segment == "occasional":
        days = random.randint(0, 180)
    else:  # new
        days = random.randint(0, 30)

    ts = now - timedelta(days=days, hours=random.randint(0, 23), minutes=random.randint(0, 59))
    return ts


def _num_items(segment: str) -> int:
    if segment == "vip":
        return random.choices([1, 2, 3, 4, 5], weights=[0.10, 0.20, 0.30, 0.25, 0.15])[0]
    return random.choices([1, 2, 3, 4, 5], weights=[0.45, 0.30, 0.15, 0.07, 0.03])[0]


def generate_order(user: dict) -> dict:
    segment   = user.get("segment", "regular")
    created   = _random_timestamp(segment)
    n_items   = _num_items(segment)

    # VIP users tend to pick pricier items
    if segment == "vip":
        pool = [p for p in ALL_PRODUCTS if p["price"] > 50]
    else:
        pool = ALL_PRODUCTS

    chosen_products = random.choices(pool, k=n_items)

    items = []
    for product in chosen_products:
        qty        = random.choices([1, 2, 3], weights=[0.70, 0.20, 0.10])[0]
        # Small price variation ±5%
        unit_price = round(product["price"] * random.uniform(0.95, 1.05), 2)
        items.append({
            "product_id":   product["product_id"],
            "product_name": product["name"],
            "category":     product["category"],
            "quantity":     qty,
            "unit_price":   unit_price,
        })

    total = round(sum(i["quantity"] * i["unit_price"] for i in items), 2)
    weight = _seasonal_weight(created)

    # Apply seasonal weight to status — more delivered in busy periods
    adjusted_delivered = min(0.95, STATUS_WEIGHTS[3] * weight)
    adjusted_weights = STATUS_WEIGHTS.copy()
    adjusted_weights[3] = adjusted_delivered

    status = random.choices(ORDER_STATUSES, weights=adjusted_weights)[0]

    # updated_at is a few days after creation for non-pending orders
    delta_days = {"pending": 0, "confirmed": 1, "shipped": 3, "delivered": 7, "cancelled": 1}
    updated = created + timedelta(days=delta_days.get(status, 0))

    return {
        "order_id":        str(uuid.uuid4()),
        "user_id":         user["user_id"],
        "user_segment":    segment,
        "user_city":       user.get("city", "Unknown"),
        "status":          status,
        "total_amount":    total,
        "item_count":      n_items,
        "items":           items,
        "payment_method":  random.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS)[0],
        "created_at":      created.isoformat(),
        "updated_at":      updated.isoformat(),
        "year":            created.year,
        "month":           created.month,
        "day_of_week":     created.strftime("%A"),
    }


def chunked(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk


def generate_orders(
    total_orders: int,
    users_file: Path,
    output_dir: Path,
    chunk_size: int = 500_000,
):
    print(f"Loading users from {users_file}...")
    users = json.loads(users_file.read_text())
    print(f"Loaded {len(users):,} users")

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {total_orders:,} orders in chunks of {chunk_size:,}...")
    generated = 0
    chunk_num  = 1

    while generated < total_orders:
        remaining  = total_orders - generated
        batch_size = min(chunk_size, remaining)

        batch = []
        for _ in range(batch_size):
            user = random.choice(users)
            batch.append(generate_order(user))

        out_file = output_dir / f"orders_chunk_{chunk_num:02d}.json"
        out_file.write_text(json.dumps(batch, ensure_ascii=False))

        generated += batch_size
        print(f"  Chunk {chunk_num:02d}: {batch_size:,} orders → {out_file}  [{generated:,}/{total_orders:,}]")
        chunk_num += 1

    print(f"\nDone. {generated:,} orders saved to {output_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--orders",     type=int, default=5_000_000)
    parser.add_argument("--users-file", type=str, default="../raw_data/users/users.json")
    parser.add_argument("--output-dir", type=str, default="../raw_data/orders")
    parser.add_argument("--chunk-size", type=int, default=500_000)
    args = parser.parse_args()

    generate_orders(
        total_orders=args.orders,
        users_file=Path(args.users_file),
        output_dir=Path(args.output_dir),
        chunk_size=args.chunk_size,
    )