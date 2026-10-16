"""Payment microservice — owns ONLY the payments table. References order_id, nothing else."""
from framework.server import Router
from framework.json_store import JsonStore


def register(router: Router, store: JsonStore):
    def create_payment(params, body):
        order_id = body.get("order_id")
        user_id = body.get("user_id")
        amount = float(body.get("amount", 0))
        if not order_id:
            return 400, {"error": "order_id required"}
        with store.write() as db:
            pid = store.next_id(db, "pay")
            db["rows"][pid] = {
                "payment_id": pid, "order_id": order_id,
                "user_id": user_id, "amount": amount, "status": "PAID",
            }
            return 200, db["rows"][pid]

    def get_payment(params, body):
        pid = params["payment_id"]
        db = store.read()
        row = db["rows"].get(pid)
        if not row:
            return 404, {"error": "payment not found", "payment_id": pid}
        return 200, row

    router.add("POST", "/payments", create_payment)
    router.add("GET", "/payments/{payment_id}", get_payment)
