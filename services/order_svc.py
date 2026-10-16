"""Order microservice — owns ONLY the orders table.
It stores order_id + foreign IDs (user_id, product_id) but never copies user/product rows.
To show a human-readable order detail, it calls user & product services by ID."""
from framework.server import Router
from framework.json_store import JsonStore
from framework import client
from framework.config import service_url


def register(router: Router, store: JsonStore):
    def create_order(params, body):
        user_id = body.get("user_id")
        product_id = body.get("product_id")
        qty = int(body.get("qty", 0))
        if not user_id or not product_id or qty <= 0:
            return 400, {"error": "user_id, product_id, qty required"}
        # price comes from product service by product_id (order DB does NOT store price)
        code, prod = client.get(f"{service_url('product')}/products/{product_id}")
        if code != 200:
            return 404, {"error": "product not found", "product_id": product_id}
        amount = round(prod["price"] * qty, 2)
        with store.write() as db:
            oid = store.next_id(db, "o")
            db["rows"][oid] = {
                "order_id": oid, "user_id": user_id, "product_id": product_id,
                "qty": qty, "amount": amount, "status": "CREATED",
            }
            return 200, db["rows"][oid]

    def get_order(params, body):
        oid = params["order_id"]
        db = store.read()
        row = db["rows"].get(oid)
        if not row:
            return 404, {"error": "order not found", "order_id": oid}
        return 200, row

    def order_detail(params, body):
        """Join across services BY ID: order -> user by user_id, order -> product by product_id."""
        oid = params["order_id"]
        db = store.read()
        row = db["rows"].get(oid)
        if not row:
            return 404, {"error": "order not found", "order_id": oid}
        _, user = client.get(f"{service_url('user')}/users/{row['user_id']}")
        _, prod = client.get(f"{service_url('product')}/products/{row['product_id']}")
        return 200, {
            "order_id": row["order_id"],
            "status": row["status"],
            "qty": row["qty"],
            "amount": row["amount"],
            "user": {"user_id": row["user_id"], "name": user.get("name")},
            "product": {"product_id": row["product_id"], "name": prod.get("name")},
        }

    def mark_paid(params, body):
        oid = params["order_id"]
        with store.write() as db:
            row = db["rows"].get(oid)
            if not row:
                return 404, {"error": "order not found"}
            row["status"] = "PAID"
            return 200, row

    router.add("POST", "/orders", create_order)
    router.add("GET", "/orders/{order_id}", get_order)
    router.add("GET", "/orders/{order_id}/detail", order_detail)
    router.add("POST", "/orders/{order_id}/mark_paid", mark_paid)
