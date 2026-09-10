from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import main
from schemas import TrainState


@pytest.fixture
def client():
    return TestClient(main.app)


def make_train_state() -> TrainState:
    now = datetime.now(timezone.utc)

    return TrainState(
        train_id="12301",
        train_name="Howrah Rajdhani Express",
        current_latitude=26.4499,
        current_longitude=80.3319,
        current_speed=78.5,
        last_station_code="CNB",
        next_station_code="PRYJ",
        timestamp=now,
        scheduled_arrival=now,
        predicted_eta=now,
        delay_minutes=0,
        confidence_score=0.85,
        status="ON_TIME",
        delay_reasons=[],
    )


def test_root_returns_backend_information(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert "app_name" in body
    assert "message" in body


def test_health_returns_ok_when_redis_is_available(client, monkeypatch):
    monkeypatch.setattr(
        main.redis_client,
        "ping",
        AsyncMock(return_value=True),
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["dependencies"]["redis"] == "ok"


def test_list_trains_returns_cached_trains(client, monkeypatch):
    trains = [
        {
            "train_id": "12301",
            "train_name": "Howrah Rajdhani Express",
            "status": "ON_TIME",
        }
    ]

    monkeypatch.setattr(
        main,
        "get_all_trains",
        AsyncMock(return_value=trains),
    )

    response = client.get("/api/trains")

    assert response.status_code == 200
    assert response.json() == trains


def test_get_train_returns_train_state(client, monkeypatch):
    state = make_train_state()

    monkeypatch.setattr(
        main,
        "get_train_state",
        AsyncMock(return_value=state),
    )

    response = client.get("/api/trains/12301")

    assert response.status_code == 200
    assert response.json()["train_id"] == "12301"
    assert response.json()["status"] == "ON_TIME"


def test_get_missing_train_returns_404(client, monkeypatch):
    monkeypatch.setattr(
        main,
        "get_train_state",
        AsyncMock(return_value=None),
    )

    response = client.get("/api/trains/UNKNOWN")

    assert response.status_code == 404
    assert response.json()["detail"] == "Train not found."


def test_post_test_train_processes_gps_event(client, monkeypatch):
    state = make_train_state()

    monkeypatch.setattr(
        main,
        "process_train_event",
        AsyncMock(return_value=state),
    )

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

    response = client.post("/api/test/train", json=payload)

    assert response.status_code == 200
    assert response.json()["train_id"] == "12301"
    assert response.json()["status"] == "ON_TIME"


def test_post_test_train_rejects_invalid_coordinates(client):
    payload = {
        "train_id": "12301",
        "current_latitude": 100,
        "current_longitude": 80.3319,
        "current_speed": 78.5,
        "last_station_code": "CNB",
        "next_station_code": "PRYJ",
    }

    response = client.post("/api/test/train", json=payload)

    assert response.status_code == 422