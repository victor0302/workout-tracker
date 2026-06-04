"""Phase 0 (3/5): ingest endpoints accept valid payloads end-to-end."""

from fastapi.testclient import TestClient

from dashboard.app import app

client = TestClient(app)


def test_vision_ingest_round_trip():
    payload = {"exercise": "squat", "reps": 3, "angle": 95.0}

    response = client.post("/ingest/vision", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}

    metrics = client.get("/metrics").json()
    assert metrics["vision"]["latest"]["exercise"] == "squat"
    assert metrics["vision"]["latest"]["reps"] == 3
    assert metrics["vision"]["latest"]["angle"] == 95.0
    assert metrics["vision"]["samples"] == 1


def test_biometric_ingest_round_trip():
    payload = {"hr": 75, "spo2": 97, "ir": 60000, "red": 50000, "finger": 1}

    response = client.post("/ingest/biometric", json=payload)
    assert response.status_code == 200

    metrics = client.get("/metrics").json()
    assert metrics["biometric"]["latest"]["hr"] == 75
    assert metrics["biometric"]["latest"]["spo2"] == 97
    assert metrics["biometric"]["samples"] == 1


def test_history_grows_in_order():
    client.post("/ingest/vision", json={"exercise": "curl", "reps": 1, "angle": 45.0})
    client.post("/ingest/vision", json={"exercise": "curl", "reps": 2, "angle": 50.0})

    history = client.get("/metrics/history").json()
    assert len(history["vision"]) == 2
    assert history["vision"][0]["reps"] == 1
    assert history["vision"][-1]["reps"] == 2


def test_ingest_rejects_malformed_payload():
    # Missing required fields shouldn't crash the server.
    response = client.post("/ingest/biometric", json={"hr": "not a number"})
    assert response.status_code == 422
