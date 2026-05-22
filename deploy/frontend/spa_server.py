from __future__ import annotations

import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(os.environ.get("WEITESTING_FRONTEND_DIST", "/opt/weitesting/frontend/dist")).resolve()
API_UPSTREAM = os.environ.get("WEITESTING_API_UPSTREAM", "http://127.0.0.1:8000").rstrip("/")
API_UPSTREAM_PARSED = urlparse(API_UPSTREAM)


class SpaHandler(SimpleHTTPRequestHandler):
    def _proxy_api(self) -> None:
        parsed = urlparse(self.path)
        target_path = parsed.path
        if parsed.query:
            target_path = f"{target_path}?{parsed.query}"

        body = None
        length = self.headers.get("Content-Length")
        if length:
            body = self.rfile.read(int(length))

        headers = {key: value for key, value in self.headers.items() if key.lower() not in {"host", "connection"}}
        headers["Host"] = API_UPSTREAM_PARSED.netloc
        headers["X-Forwarded-Proto"] = "https"
        headers["X-Forwarded-Host"] = self.headers.get("Host", "")

        connection = HTTPConnection(API_UPSTREAM_PARSED.hostname, API_UPSTREAM_PARSED.port or 80, timeout=30)
        try:
            connection.request(self.command, target_path, body=body, headers=headers)
            upstream_response = connection.getresponse()
            response_body = upstream_response.read()
            self.send_response(upstream_response.status, upstream_response.reason)
            skipped_headers = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"}
            for key, value in upstream_response.getheaders():
                if key.lower() not in skipped_headers:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response_body)
        finally:
            connection.close()

    def do_GET(self) -> None:
        if self.path.startswith("/api/") or self.path == "/api":
            self._proxy_api()
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.startswith("/api/") or self.path == "/api":
            self._proxy_api()
            return
        self.send_error(404)

    def do_PUT(self) -> None:
        if self.path.startswith("/api/") or self.path == "/api":
            self._proxy_api()
            return
        self.send_error(404)

    def do_PATCH(self) -> None:
        if self.path.startswith("/api/") or self.path == "/api":
            self._proxy_api()
            return
        self.send_error(404)

    def do_DELETE(self) -> None:
        if self.path.startswith("/api/") or self.path == "/api":
            self._proxy_api()
            return
        self.send_error(404)

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        rel = unquote(parsed.path).lstrip("/")
        candidate = (ROOT / rel).resolve()
        try:
            candidate.relative_to(ROOT)
        except ValueError:
            return str(ROOT / "index.html")
        if candidate.exists():
            return str(candidate)
        if "." not in Path(parsed.path).name:
            return str(ROOT / "index.html")
        return str(candidate)

    def log_message(self, format: str, *args) -> None:
        return


if __name__ == "__main__":
    host = os.environ.get("WEITESTING_FRONTEND_HOST", "127.0.0.1")
    port = int(os.environ.get("WEITESTING_FRONTEND_PORT", "18080"))
    server = ThreadingHTTPServer((host, port), SpaHandler)
    server.serve_forever()
