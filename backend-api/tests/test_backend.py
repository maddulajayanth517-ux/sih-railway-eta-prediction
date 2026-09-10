import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import main


class BackendContractTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_root_and_health(self):
        root = self.client.get("/")
        self.assertEqual(root.status_code, 200)
        self.assertIn("app_name", root.json())

        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertIn(health.json()["status"], {"ok", "degraded"})

    def test_test_train_endpoint_processes_status(self):
        payload = {
            "train_id": "12301",
            "train_name": "Howrah Rajdhani Express",
            "current_latitude": 26.4499,
            "current_longitude": 80.3319,
            "current_speed": 78.5,
            "last_station_code": "CNB",
            "next_station_code": "PRYJ",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        response = self.client.post("/api/test/train", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["train_id"], "12301")
        self.assertIn(body["status"], {"ON_TIME", "DELAYED", "GPS_LOST"})

    def test_missing_train_returns_404(self):
        response = self.client.get("/api/trains/NOT_FOUND")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
