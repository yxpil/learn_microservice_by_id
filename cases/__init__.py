"""Demo cases: show microservices chained by unique IDs, each DB owning one function."""
from framework import client, gateway
from framework.config import service_url


def banner(t):
    print(f"\n--- {t} ---")


def case1_normal_order(u, p):
    banner("Case 1: normal order — deduct balance + stock, record payment")
    r = gateway.place_order(u["user_id"], p["product_id"], qty=2)
    print("order:", r["order"]["order_id"], "amount", r["order"]["amount"], "status", r["order"]["status"])
    print("user balance now:", r["user"]["balance"])
    print("product stock now:", r["product"]["stock"])
    print("payment:", r["payment"]["payment_id"], r["payment"]["status"])
    # join detail across services by ID
    d = gateway.order_detail(r["order"]["order_id"])
    print("detail (joined by ID):", d["user"]["name"], "->", d["product"]["name"], "x", d["qty"])
    assert r["order"]["status"] == "PAID"


def case2_insufficient_balance(u, p):
    banner("Case 2: insufficient balance — order fails at deduct step")
    # a fresh poor user
    _, poor = client.post(f"{service_url('user')}/users", {"name": "poor", "balance": 5.0})
    try:
        gateway.place_order(poor["user_id"], p["product_id"], qty=1)
        print("ERROR: should have failed")
    except gateway.OrderError as e:
        print("expected failure at", e.step, "->", e.payload.get("error"))
        # stock must be untouched (order failed before deduct_stock)
        _, prod = client.get(f"{service_url('product')}/products/{p['product_id']}")
        print("stock unchanged:", prod["stock"])


def case3_out_of_stock(u, p):
    banner("Case 3: out of stock — deduct balance refunded as compensation")
    # a product with 0 stock
    _, zero = client.post(f"{service_url('product')}/products",
                          {"name": "soldout", "price": 50.0, "stock": 0})
    try:
        gateway.place_order(u["user_id"], zero["product_id"], qty=1)
        print("ERROR: should have failed")
    except gateway.OrderError as e:
        print("expected failure at", e.step, "->", e.payload.get("error"))
        # balance was refunded: alice balance should be back to 1000 - 240(case1) = 760
        _, alice = client.get(f"{service_url('user')}/users/{u['user_id']}")
        print("alice balance after refund:", alice["balance"])


def case4_order_join_by_id(u, p):
    banner("Case 4: order detail — order DB does NOT store names; it calls user/product by ID")
    r = gateway.place_order(u["user_id"], p["product_id"], qty=1)
    oid = r["order"]["order_id"]
    # raw order row: only IDs, no names
    _, raw = client.get(f"{service_url('order')}/orders/{oid}")
    print("raw order row (order DB only has IDs):", raw)
    # detail endpoint joins across services by ID
    d = gateway.order_detail(oid)
    print("joined detail:", d["user"]["name"], "buying", d["qty"], "x", d["product"]["name"])


def run_all_cases(u, p):
    case1_normal_order(u, p)
    case2_insufficient_balance(u, p)
    case3_out_of_stock(u, p)
    case4_order_join_by_id(u, p)
    print("\n== all cases done ==")
