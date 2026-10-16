"""API gateway: orchestrates an order across microservices BY ID.
Each service owns its own DB; the gateway only chains HTTP calls with IDs."""
from framework import client
from framework.config import service_url


class OrderError(Exception):
    def __init__(self, step, code, payload):
        self.step = step
        self.code = code
        self.payload = payload
        super().__init__(f"{step}: {code} {payload}")


def place_order(user_id: str, product_id: str, qty: int):
    # 1. order service creates an order row (looks up price from product by ID)
    code, order = client.post(f"{service_url('order')}/orders",
                              {"user_id": user_id, "product_id": product_id, "qty": qty})
    if code != 200:
        raise OrderError("create_order", code, order)
    order_id = order["order_id"]
    amount = order["amount"]

    # 2. user service deducts balance (by user_id)
    code, user = client.post(f"{service_url('user')}/users/{user_id}/deduct",
                            {"amount": amount})
    if code != 200:
        raise OrderError("deduct_balance", code, {**user, "order_id": order_id})

    # 3. product service deducts stock (by product_id)
    code, prod = client.post(f"{service_url('product')}/products/{product_id}/deduct_stock",
                            {"qty": qty})
    if code != 200:
        # compensation: refund balance since stock failed
        client.post(f"{service_url('user')}/users/{user_id}/deduct", {"amount": -amount})
        raise OrderError("deduct_stock", code, {**prod, "order_id": order_id})

    # 4. payment service records payment (by order_id)
    code, pay = client.post(f"{service_url('payment')}/payments",
                            {"order_id": order_id, "user_id": user_id, "amount": amount})
    if code != 200:
        raise OrderError("create_payment", code, {**pay, "order_id": order_id})

    # 5. mark order paid
    _, paid = client.post(f"{service_url('order')}/orders/{order_id}/mark_paid", {})
    return {"order": paid, "user": user, "product": prod, "payment": pay}


def order_detail(order_id: str):
    # order service joins user + product BY ID on the fly
    code, detail = client.get(f"{service_url('order')}/orders/{order_id}/detail")
    if code != 200:
        raise OrderError("order_detail", code, detail)
    return detail
