import http.client
import json
import threading
import unittest

import app
from task_store import TaskStore


class ApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.STORE = TaskStore()
        app.REQUEST_COUNTS.clear()
        app.DEMO_ALERT = False
        cls.server = app.create_server(host="127.0.0.1", port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        headers = {}
        encoded = None
        if body is not None:
            encoded = json.dumps(body)
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=encoded, headers=headers)
        response = conn.getresponse()
        raw = response.read().decode("utf-8")
        content_type = response.getheader("Content-Type", "")
        conn.close()
        if "application/json" in content_type:
            return response.status, json.loads(raw)
        return response.status, raw

    def test_health(self):
        status, body = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_crud_flow(self):
        status, created = self.request("POST", "/tasks", {"title": "Pipeline demo"})
        self.assertEqual(status, 201)
        task_id = created["id"]

        status, updated = self.request("PUT", f"/tasks/{task_id}", {"completed": True})
        self.assertEqual(status, 200)
        self.assertTrue(updated["completed"])

        status, fetched = self.request("GET", f"/tasks/{task_id}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["id"], task_id)

        status, deleted = self.request("DELETE", f"/tasks/{task_id}")
        self.assertEqual(status, 200)
        self.assertEqual(deleted["id"], task_id)

    def test_metrics_and_alert_toggle(self):
        status, metrics = self.request("GET", "/metrics")
        self.assertEqual(status, 200)
        self.assertIn("tasktracker_http_requests_total", metrics)

        status, body = self.request("POST", "/simulate-alert")
        self.assertEqual(status, 200)
        self.assertTrue(body["demo_alert"])

        _, metrics = self.request("GET", "/metrics")
        self.assertIn("tasktracker_demo_alert 1", metrics)

        self.request("POST", "/reset-alert")


if __name__ == "__main__":
    unittest.main()
