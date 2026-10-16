"""Launch one microservice process: python node_entry.py <name>
Each process owns one JSON DB and listens on its own port."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework.server import Router, serve
from framework.json_store import JsonStore
from framework.config import SERVICES, db_path
from services import user_svc, product_svc, order_svc, payment_svc


REGISTRY = {
    "user": user_svc,
    "product": product_svc,
    "order": order_svc,
    "payment": payment_svc,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in REGISTRY:
        print("usage: python node_entry.py <user|product|order|payment>")
        sys.exit(1)
    name = sys.argv[1]
    port = SERVICES[name]["port"]
    store = JsonStore(db_path(name))
    router = Router()
    router.add("GET", "/health", lambda params, body: (200, {"ok": True, "service": name}))
    REGISTRY[name].register(router, store)
    print(f"[{name}] listening on :{port}  db={SERVICES[name]['db']}")
    serve(router, port)


if __name__ == "__main__":
    main()
