"""
Generate synthetic user profiles.
Usage:
    python generate_users.py --count 100000 --output ../raw_data/users/users.json
"""
import uuid
import json
import argparse
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from faker_config import fake, CITIES


def generate_user(user_index: int) -> dict:
    # Spread registration dates over 2 years
    days_ago     = random.randint(0, 730)
    registered   = datetime.now(timezone.utc) - timedelta(days=days_ago)

    # Assign user segment — drives purchasing behavior in order generator
    segment = random.choices(
        ["vip", "regular", "occasional", "new"],
        weights=[0.05, 0.35, 0.40, 0.20],
    )[0]

    return {
        "user_id":        str(uuid.uuid4()),
        "username":       fake.user_name(),
        "email":          fake.email(),
        "full_name":      fake.name(),
        "city":           random.choice(CITIES),
        "segment":        segment,
        "age":            random.randint(18, 65),
        "registered_at":  registered.isoformat(),
    }


def generate_users(count: int, output_path: Path) -> list:
    print(f"Generating {count:,} users...")
    users = [generate_user(i) for i in range(count)]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(users, indent=2, ensure_ascii=False))

    print(f"Saved {len(users):,} users → {output_path}")
    return users


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count",  type=int,  default=100_000)
    parser.add_argument("--output", type=str,  default="../raw_data/users/users.json")
    args = parser.parse_args()
    generate_users(args.count, Path(args.output))