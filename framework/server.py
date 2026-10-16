"""Minimal HTTP service skeleton: routes -> handler funcs. Each microservice runs one."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Router:
    def __init__(self):
        self.routes = []  # (method, path_pattern, handler)

    def add(self, method: str, path: str, handler):
        # path like "/users/{user_id}" -> regex-ish matcher
        self.routes.append((method, path, handler))

    def match(self, method: str, path: str):
        for m, pat, handler in self.routes:
            if m != method:
                continue
            pat_parts = pat.strip("/").split("/")
            path_parts = path.strip("/").split("/")
            if len(pat_parts) != len(path_parts):
                continue
            params = {}
            ok = True
            for pp, ap in zip(pat_parts, path_parts):
                if pp.startswith("{") and pp.endswith("}"):
                    params[pp[1:-1]] = ap
                elif pp != ap:
                    ok = False
                    break
            if ok:
                return handler, params
        return None, None


def make_handler(router: Router):
    class H(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self):
            length = int(self.headers.get("Content-Length", 0) or 0)
            if not length:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            try:
                return json.loads(raw) if raw else {}
            except Exception:
                return {}

        def do_GET(self):
            path = self.path.split("?")[0]
            handler, params = router.match("GET", path)
            if not handler:
                return self._send(404, {"error": "not found", "path": path})
            try:
                code, obj = handler(params, self._read_body())
                self._send(code, obj)
            except Exception as e:
                self._send(500, {"error": str(e)})

        def do_POST(self):
            path = self.path.split("?")[0]
            handler, params = router.match("POST", path)
            if not handler:
                return self._send(404, {"error": "not found", "path": path})
            try:
                code, obj = handler(params, self._read_body())
                self._send(code, obj)
            except Exception as e:
                self._send(500, {"error": str(e)})

        def log_message(self, *args):
            pass  # quiet
    return H


def serve(router: Router, port: int):
    httpd = ThreadingHTTPServer(("0.0.0.0", port), make_handler(router))
    httpd.serve_forever()
