"""FastAPI dashboard.

Ingests samples from the vision tracker and the BLE listener, holds
recent state in memory and exposes everything as JSON on /metrics.

Run with:
    uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 --reload
"""

from collections import deque
from time import time
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

MAX_HISTORY = 300  # ~5 minutes at 1 Hz

app = FastAPI(title="workout-tracker dashboard")


class VisionSample(BaseModel):
    exercise: str = "unknown"
    reps: int = 0
    angle: float | None = None


class BiometricSample(BaseModel):
    hr: int = 0
    spo2: int = 0
    ir: int = 0
    red: int = 0
    finger: int = 0


class State:
    def __init__(self) -> None:
        self.vision_latest: dict[str, Any] | None = None
        self.biometric_latest: dict[str, Any] | None = None
        self.vision_history: deque[dict[str, Any]] = deque(maxlen=MAX_HISTORY)
        self.biometric_history: deque[dict[str, Any]] = deque(maxlen=MAX_HISTORY)


state = State()


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "workout-tracker dashboard"}


@app.post("/ingest/vision")
def ingest_vision(sample: VisionSample) -> dict[str, str]:
    record = sample.model_dump() | {"ts": time()}
    state.vision_latest = record
    state.vision_history.append(record)
    return {"status": "accepted"}


@app.post("/ingest/biometric")
def ingest_biometric(sample: BiometricSample) -> dict[str, str]:
    record = sample.model_dump() | {"ts": time()}
    state.biometric_latest = record
    state.biometric_history.append(record)
    return {"status": "accepted"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return {
        "vision": {
            "latest": state.vision_latest,
            "samples": len(state.vision_history),
        },
        "biometric": {
            "latest": state.biometric_latest,
            "samples": len(state.biometric_history),
        },
    }


@app.get("/metrics/history")
def metrics_history() -> dict[str, list[dict[str, Any]]]:
    return {
        "vision": list(state.vision_history),
        "biometric": list(state.biometric_history),
    }
