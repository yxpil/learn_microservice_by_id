"""Shared config: every microservice owns one JSON DB, talks to others only by HTTP + ID."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# One service = one process = one database. No shared tables, no cross-DB foreign keys.
SERVICES = {
    "user":    {"port": 7001, "db": "user.json"},     # only users
    "product": {"port": 7002, "db": "product.json"},  # only products
    "order":   {"port": 7003, "db": "order.json"},    # only orders (refs user_id/product_id)
    "payment": {"port": 7004, "db": "payment.json"}, # only payments (refs order_id)
}

def service_url(name: str) -> str:
    return f"http://127.0.0.1:{SERVICES[name]['port']}"

def db_path(name: str) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, SERVICES[name]["db"])
