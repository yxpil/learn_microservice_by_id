"""User microservice — owns ONLY the users table. No balance/stock/order data here."""
from framework.server import Router
from framework.json_store import JsonStore


def register(router: Router, store: JsonStore):
    def create_user(params, body):
        name = body.get("name")
        balance = float(body.get("balance", 0))
        if not name:
            return 400, {"error": "name required"}
        with store.write() as db:
            uid = store.next_id(db, "u")
            db["rows"][uid] = {"user_id": uid, "name": name, "balance": balance}
            return 200, db["rows"][uid]

    def get_user(params, body):
        uid = params["user_id"]
        db = store.read()
        row = db["rows"].get(uid)
        if not row:
            return 404, {"error": "user not found", "user_id": uid}
        return 200, row

    def deduct(params, body):
        uid = params["user_id"]
        amount = float(body.get("amount", 0))
        with store.write() as db:
            row = db["rows"].get(uid)
            if not row:
                return 404, {"error": "user not found"}
            if row["balance"] < amount:
                return 409, {"error": "insufficient balance",
                             "user_id": uid, "balance": row["balance"], "need": amount}
            row["balance"] = round(row["balance"] - amount, 2)
            return 200, {"user_id": uid, "balance": row["balance"], "deducted": amount}

    router.add("POST", "/users", create_user)
    router.add("GET", "/users/{user_id}", get_user)
    router.add("POST", "/users/{user_id}/deduct", deduct)
