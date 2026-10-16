"""One-click: spawn 4 microservice processes, seed data, run demo cases, then shut down."""
import subprocess
import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import client
from framework.config import service_url, DATA_DIR, SERVICES


def wait_up(name, timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            code, _ = client.get(f"{service_url(name)}/health", timeout=0.5)
            if code == 200:
                return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"service {name} did not start")


def seed():
    # create a user and a product
    _, u = client.post(f"{service_url('user')}/users", {"name": "alice", "balance": 1000.0})
    _, p = client.post(f"{service_url('product')}/products",
                       {"name": "keyboard", "price": 120.0, "stock": 10})
    return u, p


def main():
    # fresh data dir
    if os.path.exists(DATA_DIR):
        import shutil; shutil.rmtree(DATA_DIR)
    os.makedirs(DATA_DIR, exist_ok=True)

    procs = []
    try:
        for name in SERVICES:
            procs.append(subprocess.Popen(
                [sys.executable, "node_entry.py", name],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            time.sleep(0.3)

        for name in SERVICES:
            wait_up(name)
        print("== all 4 microservices up ==")

        u, p = seed()
        print(f"seeded user={u['user_id']} balance={u['balance']}")
        print(f"seeded product={p['product_id']} price={p['price']} stock={p['stock']}")

        # import and run cases
        from cases import run_all_cases
        run_all_cases(u, p)

    finally:
        for pr in procs:
            pr.terminate()
        print("== all services stopped ==")


if __name__ == "__main__":
    main()
