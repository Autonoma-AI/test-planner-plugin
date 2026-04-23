#!/usr/bin/env python3
"""Tiny login fixture app for login-probe tests.

Endpoints:
  GET  /login      -> HTML form (username, password)
  POST /login      -> checks demo/demo123, sets Set-Cookie: session=valid-token; Path=/
  GET  /dashboard  -> if session cookie == valid-token => 200 with marker
                      else 302 Location: /login

Intentionally dependency-free (stdlib only) so pytest can bring it up
in-process without touching the user's Python env.
"""
from __future__ import annotations

import argparse
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

VALID_USER = "demo"
VALID_PASS = "demo123"
VALID_TOKEN = "valid-token"

LOGIN_HTML = """<!doctype html>
<html><body>
<h1>Login</h1>
<form method="post" action="/login">
  <input name="username" id="username" />
  <input name="password" id="password" type="password" />
  <button type="submit" id="submit">Sign in</button>
</form>
</body></html>
"""

DASH_HTML = """<!doctype html>
<html><body>
<h1>Dashboard</h1>
<span data-testid="user-menu">demo</span>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_a, **_k):
        return

    def _cookie(self) -> str | None:
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        jar = SimpleCookie()
        jar.load(raw)
        if "session" in jar:
            return jar["session"].value
        return None

    def do_GET(self):  # noqa: N802
        if self.path == "/login":
            body = LOGIN_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/dashboard":
            if self._cookie() == VALID_TOKEN:
                body = DASH_HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):  # noqa: N802
        if self.path != "/login":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        form = {k: v[0] for k, v in parse_qs(raw).items()}
        if form.get("username") == VALID_USER and form.get("password") == VALID_PASS:
            self.send_response(302)
            self.send_header("Location", "/dashboard")
            self.send_header("Set-Cookie", f"session={VALID_TOKEN}; Path=/")
            self.end_headers()
            return
        self.send_response(302)
        self.send_header("Location", "/login?error=1")
        self.end_headers()


def serve(host: str = "127.0.0.1", port: int = 0) -> tuple[ThreadingHTTPServer, threading.Thread]:
    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    srv, _ = serve(port=args.port)
    print(f"listening on http://127.0.0.1:{srv.server_address[1]}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
