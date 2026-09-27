"""Task Tracker API implemented with the Python standard library.

Endpoints:
  GET  /health
  GET  /tasks
  POST /tasks
  GET  /tasks/<id>
  PUT  /tasks/<id>
  DELETE /tasks/<id>
  GET  /metrics
  POST /simulate-alert
  POST /reset-alert
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlparse

from task_store import TaskStore

STORE = TaskStore()
REQUEST_LOCK = Lock()
REQUEST_COUNTS: dict[tuple[str, str, int], int] = {}
DEMO_ALERT = False


def record_request(method: str, path: str, status: int) -> None:
    key = (method, path, status)
    with REQUEST_LOCK:
        REQUEST_COUNTS[key] = REQUEST_COUNTS.get(key, 0) + 1


def metrics_text() -> str:
    lines = [
        "# HELP tasktracker_tasks_total Number of tasks currently stored.",
        "# TYPE tasktracker_tasks_total gauge",
        f"tasktracker_tasks_total {STORE.count()}",
        "# HELP tasktracker_demo_alert Demo alert metric used to prove alert delivery.",
        "# TYPE tasktracker_demo_alert gauge",
        f"tasktracker_demo_alert {1 if DEMO_ALERT else 0}",
        "# HELP tasktracker_http_requests_total HTTP requests handled by the API.",
        "# TYPE tasktracker_http_requests_total counter",
    ]
    with REQUEST_LOCK:
        for (method, path, status), count in sorted(REQUEST_COUNTS.items()):
            safe_path = path.replace('"', '\\"')
            lines.append(
                f'tasktracker_http_requests_total{{method="{method}",path="{safe_path}",status="{status}"}} {count}'
            )
    return "\n".join(lines) + "\n"


class TaskTrackerHandler(BaseHTTPRequestHandler):
    server_version = "TaskTracker/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("request body must be valid JSON") from exc
        if not isinstance(body, dict):
            raise TypeError("request body must be a JSON object")
        return body

    def _send_json(self, status: int, payload: dict | list) -> None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        record_request(self.command, urlparse(self.path).path, status)

    def _send_text(self, status: int, text: str, content_type: str) -> None:
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        record_request(self.command, urlparse(self.path).path, status)

    @staticmethod
    def _task_id(path: str) -> int | None:
        pieces = [piece for piece in path.split("/") if piece]
        if len(pieces) == 2 and pieces[0] == "tasks" and pieces[1].isdigit():
            return int(pieces[1])
        return None

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "ok", "environment": os.getenv("APP_ENV", "development")})
            return
        if path == "/tasks":
            self._send_json(200, STORE.list_tasks())
            return
        if path == "/metrics":
            self._send_text(200, metrics_text(), "text/plain; version=0.0.4")
            return
        task_id = self._task_id(path)
        if task_id is not None:
            try:
                self._send_json(200, STORE.get_task(task_id))
            except KeyError as exc:
                self._send_json(404, {"error": str(exc)})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        global DEMO_ALERT
        path = urlparse(self.path).path
        try:
            if path == "/tasks":
                body = self._json_body()
                self._send_json(201, STORE.create_task(body.get("title")))
                return
            if path == "/simulate-alert":
                DEMO_ALERT = True
                self._send_json(200, {"demo_alert": True})
                return
            if path == "/reset-alert":
                DEMO_ALERT = False
                self._send_json(200, {"demo_alert": False})
                return
            self._send_json(404, {"error": "not found"})
        except (ValueError, TypeError) as exc:
            self._send_json(400, {"error": str(exc)})

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        task_id = self._task_id(path)
        if task_id is None:
            self._send_json(404, {"error": "not found"})
            return
        try:
            body = self._json_body()
            self._send_json(
                200,
                STORE.update_task(task_id, title=body.get("title"), completed=body.get("completed")),
            )
        except KeyError as exc:
            self._send_json(404, {"error": str(exc)})
        except (ValueError, TypeError) as exc:
            self._send_json(400, {"error": str(exc)})

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        task_id = self._task_id(path)
        if task_id is None:
            self._send_json(404, {"error": "not found"})
            return
        try:
            self._send_json(200, STORE.delete_task(task_id))
        except KeyError as exc:
            self._send_json(404, {"error": str(exc)})


def create_server(host: str = "0.0.0.0", port: int = 8000) -> ThreadingHTTPServer:  # nosec B104
    return ThreadingHTTPServer((host, port), TaskTrackerHandler)


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    server = create_server(port=port)
    print(f"Task Tracker API listening on port {server.server_address[1]}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
