"""Tiny webhook receiver used only to demonstrate Alertmanager delivery."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = Path("/monitoring/alerts.log")


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):  # noqa: N802
        if self.path != "/alerts":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        payload = json.loads(raw or "{}")
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
        self._send(200, {"received": True})

    def do_GET(self):  # noqa: N802
        if self.path != "/received":
            self._send(404, {"error": "not found"})
            return
        count = 0
        if LOG.exists():
            count = sum(1 for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip())
        self._send(200, {"count": count})

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9095), Handler).serve_forever()
