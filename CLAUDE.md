# CLAUDE.md

Guidance for Claude sessions working on this repo.

## What this project is

Fitness tracking system that fuses computer vision (rep counting,
exercise classification) with wearable biometrics (HR / SpO2 from an
ESP32 + MAX30102), surfaced through a FastAPI dashboard.

Read `notes.md` for the full plan, phases and open questions. Read
`decisions.md` for design and process decisions made along the way
(squash-merge default, no `Co-Authored-By` in commits, branch naming,
test-over-runbook policy).

## Repo layout

- `vision/` — MediaPipe pose estimator, rep counter (state machine on a
  joint-angle signal), exercise classifier (currently a stub). Entry
  point: `python -m vision.main --source 0`.
- `firmware/esp32_max30102/` — Arduino sketch. Reads MAX30102 over I2C,
  broadcasts a JSON payload via a single BLE notify characteristic. HR
  works; SpO2 algorithm is stubbed.
- `ble_listener/` — `bleak` client. Scans for `WorkoutBand`, subscribes
  to the characteristic, forwards each JSON sample to the dashboard.
- `dashboard/` — FastAPI. `POST /ingest/vision`, `POST /ingest/biometric`,
  `GET /metrics`, `GET /metrics/history`. State is in-memory; no
  persistence yet (that's Phase 4).

BLE UUIDs in `firmware/esp32_max30102/esp32_max30102.ino` and
`ble_listener/listener.py` must match — change them in pairs.

## Conventions

- Python 3.11+ syntax (PEP 604 unions, etc.).
- No comments unless the *why* is non-obvious. Don't restate what the
  code already says.
- Keep components decoupled. The only contract between them is the
  dashboard's POST schemas (`VisionSample`, `BiometricSample` in
  `dashboard/app.py`). Don't add direct imports across components.
- Each component must run standalone — the dashboard is optional for
  developing vision or the BLE listener (both swallow connection errors).
- Tests live under `tests/`, run with `pytest`. A state-reset fixture
  in `tests/conftest.py` resets the dashboard's in-memory state between
  tests, so order doesn't matter.
- Branches: `phaseN/MM-slug` for ticket work, `docs/<slug>` for docs.
- Merge PRs with `gh pr merge N --squash --delete-branch`.
- **No `Co-Authored-By: Claude` trailer on commits or PRs.**

## Status

Scaffold and **Phase 0 complete** (2026-06-04). Phase 1 (9 tickets,
#6–#14) is the next phase to work — start with the record-and-replay
harness (#6). Phases 2–6 are described in `notes.md` but not yet
broken into tickets.

## When working on Phase 1

The rep counter currently uses a naive threshold on a single knee
angle. **Do not tune those thresholds in isolation.** The first two
Phase 1 tickets build a record-and-replay harness and a labeled
regression set; every later Phase 1 ticket validates against that set.
If you find yourself adjusting threshold constants without rerunning
the regression test, stop.
