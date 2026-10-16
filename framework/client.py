"""Minimal JSON HTTP client for inter-service calls (service A -> service B by ID)."""
import json
import urllib.request
import urllib.error


def _request(method: str, url: str, body: dict | None = None, timeout: float = 5.0):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8")
            return resp.status, (json.loads(payload) if payload else {})
    except urllib.error.HTTPError as e:
        payload = e.read().decode("utf-8")
        try:
            return e.code, json.loads(payload)
        except Exception:
            return e.code, {"error": payload}


def get(url: str, timeout: float = 5.0):
    return _request("GET", url, None, timeout)


def post(url: str, body: dict, timeout: float = 5.0):
    return _request("POST", url, body, timeout)
