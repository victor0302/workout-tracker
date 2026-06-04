"""Phase 0 (4/5): vision → dashboard wire is contract-correct.

The acceptance criterion in the ticket ("pose overlay appears, /metrics
updates ~1 Hz") needs a real webcam. We can't run that automatically;
what we *can* do is prove that the payload vision/main.py would emit
is accepted by the dashboard schema and shows up in /metrics correctly.

If this test passes, then the only remaining failure modes are
hardware (no camera, no pose detection) — not data-shape mismatches.
"""

from fastapi.testclient import TestClient

from dashboard.app import app
from vision.main import build_vision_payload

client = TestClient(app)


def test_payload_shape_accepted_by_dashboard():
    payload = build_vision_payload(exercise="squat", reps=5, angle=88.0)

    response = client.post("/ingest/vision", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}


def test_payload_contents_visible_in_metrics():
    payload = build_vision_payload(exercise="deadlift", reps=12, angle=170.0)
    client.post("/ingest/vision", json=payload)

    latest = client.get("/metrics").json()["vision"]["latest"]
    assert latest["exercise"] == "deadlift"
    assert latest["reps"] == 12
    assert latest["angle"] == 170.0


def test_payload_unknown_exercise_still_accepted():
    # Classifier returns "unknown" until Phase 3 is built; dashboard must accept it.
    payload = build_vision_payload(exercise="unknown", reps=0, angle=180.0)

    response = client.post("/ingest/vision", json=payload)
    assert response.status_code == 200
