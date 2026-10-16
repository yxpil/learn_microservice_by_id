"""Product microservice — owns ONLY the products table. No user/order/payment data here."""
from framework.server import Router
from framework.json_store import JsonStore


def register(router: Router, store: JsonStore):
    def create_product(params, body):
        name = body.get("name")
        price = float(body.get("price", 0))
        stock = int(body.get("stock", 0))
        if not name:
            return 400, {"error": "name required"}
        with store.write() as db:
            pid = store.next_id(db, "p")
            db["rows"][pid] = {"product_id": pid, "name": name,
                               "price": price, "stock": stock}
            return 200, db["rows"][pid]

    def get_product(params, body):
        pid = params["product_id"]
        db = store.read()
        row = db["rows"].get(pid)
        if not row:
            return 404, {"error": "product not found", "product_id": pid}
        return 200, row

    def deduct_stock(params, body):
        pid = params["product_id"]
        qty = int(body.get("qty", 0))
        with store.write() as db:
            row = db["rows"].get(pid)
            if not row:
                return 404, {"error": "product not found"}
            if row["stock"] < qty:
                return 409, {"error": "out of stock",
                             "product_id": pid, "stock": row["stock"], "need": qty}
            row["stock"] -= qty
            return 200, {"product_id": pid, "stock": row["stock"], "deducted": qty}

    router.add("POST", "/products", create_product)
    router.add("GET", "/products/{product_id}", get_product)
    router.add("POST", "/products/{product_id}/deduct_stock", deduct_stock)
