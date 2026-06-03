# workout-tracker — working notes

Living doc capturing what's been decided. Not a spec — update as decisions change.

## What this project is

A fitness tracking system that fuses two independent data sources:

- **Vision (camera).** MediaPipe pose → joint angles → rep counting and
  exercise classification. Knows about *movement*.
- **Wearable (ESP32 + MAX30102).** Heart rate and SpO2 over BLE. Knows
  about *physiology*.

A FastAPI dashboard ingests from both and is where they get correlated
(HR recovery between sets, intensity vs. rep tempo, etc.).

## Component layout

```
vision/                    MediaPipe + rep counter + exercise classifier
firmware/esp32_max30102/   Arduino sketch for the wearable
ble_listener/              bleak client that forwards BLE samples
dashboard/                 FastAPI ingest + /metrics
```

Components are decoupled — the only contract between them is the
dashboard's POST schemas. Each runs independently; the dashboard is
optional during vision / BLE development (both swallow connection
failures so you can develop without it).

## Plan — 6 phases

Scaffold is done; everything below is the actual work.

- **Phase 0 — Smoke test.** Prove every pipe in the scaffold works
  end-to-end with mock data before building anything real.
- **Phase 1 — Rep counting that works.** Squats only. Replace the
  threshold hack with a real counter: smoothing, hysteresis, depth
  gate, regression set.
- **Phase 2 — Wearable: real HR flowing.** Flash the ESP32, validate
  MAX30102 readings against a reference, fill in the SpO2 algorithm
  that's stubbed in the sketch.
- **Phase 3 — Exercise classifier.** Collect labeled keypoint clips,
  train a small temporal model (1D CNN / GRU), wire into the existing
  classifier stub.
- **Phase 4 — Dashboard: persistence + UI.** SQLite for sessions / reps
  / HR history. Web page that charts HR and rep count in real time.
- **Phase 5 — Session + correlation analytics.** Detect set boundaries
  from rest gaps, compute HR recovery, volume per exercise, intensity
  scoring. The phase where the two data sources finally pay off
  together.
- **Phase 6 (optional) — Productize.** Auth, multi-user, deploy.

Phases 1 and 2 are independent and can run in parallel.

## Key tradeoffs we flagged

- **Phase 3 is the biggest by far.** It's the only ML phase. Can be
  deferred indefinitely by manually telling the dashboard which
  exercise is in progress; everything else still works without it.
- **Phase 1 tasks "1/9" and "2/9" feel like overhead but aren't.** The
  record-and-replay harness + labeled regression set are
  highest-leverage; every later Phase 1 task gets faster once they
  exist. Skipping them makes Phase 1 take ~3× longer.

## Current status

- Scaffold committed and pushed to `victor0302/workout-tracker` (public).
- Phase 0 and Phase 1 broken out as GitHub issues (`gh issue list`).
- Phases 2–6 are not broken into tickets yet — do that when you get there.
- Next action: start Phase 0 (1/5).

## Open questions

- Repo visibility is currently public — confirm long-term.
- Which exercises beyond squat / curl / deadlift matter? Affects Phase 3
  data collection.
- Single-user dashboard for now; multi-user is Phase 6.
