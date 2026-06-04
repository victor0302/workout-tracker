"""Phase 0 (2/5): the dashboard boots and base endpoints respond."""

from fastapi.testclient import TestClient

from dashboard.app import app

client = TestClient(app)


def test_root_returns_ok():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "workout-tracker dashboard",
    }


def test_metrics_empty_state_shape():
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["vision"] == {"latest": None, "samples": 0}
    assert body["biometric"] == {"latest": None, "samples": 0}


def test_metrics_history_empty_state():
    response = client.get("/metrics/history")
    assert response.status_code == 200
    body = response.json()
    assert body == {"vision": [], "biometric": []}
