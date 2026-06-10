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

- **Phase 0 — Smoke test. ✅ DONE 2026-06-04.** All five acceptance
  criteria encoded as pytest tests under `tests/`. Tickets #1–#5
  closed via PRs #15–#19.
- **Phase 1 — Rep counting that works.** Squats only. Replace the
  threshold hack with a real counter: smoothing, hysteresis, depth
  gate, regression set. **In progress — 4/9 merged, #10 in flight
  (PR #28).**
- **Phase 1.5 — Rep-counter extensions.** Per-rep metrics
  (depth, tempo, asymmetry), calibration, multi-exercise support,
  real-clip regression set, replay viewer, A/B tuning harness, set
  boundaries. 10 tickets (#29–#38) opened 2026-06-08. Not required to
  ship Phase 1; valuable for Phase 4 analytics and longer-term use.
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
- **Phase 0 complete.** Tickets #1–#5 closed via PRs #15–#19,
  squash-merged to main on 2026-06-04. Acceptance criteria live as
  pytest tests under `tests/`.
- **Phase 1 in flight (4/9).** Merged so far:
  - `#6` — record-and-replay harness (PR #21, 2026-06-06).
    `vision/replay.py` runs a JSONL clip through the rep counter
    headless.
  - `#7` — synthetic regression set (PR #22, 2026-06-06).
    `regression_set/` holds 7 labeled synthetic clips covering every
    Phase 1 failure mode.
  - `#8` — averaged knee angle (PR #24, 2026-06-07). New
    `vision/signal.py` houses signal extraction. `knee_angle()`
    averages both legs when visible, falls back to one side, returns
    `None` when neither leg meets the visibility threshold.
  - `#9` — EMA + median smoothing (PR #26, 2026-06-07). `Smoother`
    Protocol in `signal.py`; `EMASmoother(alpha=0.3)` is the default
    wired into `main.py` and `replay.py`. Side effect: smoothing
    alone dropped `jitter_0reps` from 14 → 0. Only `partial_0reps`
    still fails the counter (3 vs expected 0).
  - `#10` hysteresis (PR #28, **in flight**). Extends `RepCounter`
    with `dwell_frames=5` — state machine only commits a transition
    after N consecutive frames past the threshold. Required a
    generator change: every synthetic clip now has a 15-frame
    trailing buffer of standing pose so the last up-transition can
    commit before EOF (real recordings have this naturally).
    Regression counts unchanged across all clips.
  - 4 tickets remaining: `#11` depth gate → `#12` min-duration →
    `#13` debug overlay → `#14` regression test. `#11–#12` extend
    `RepCounter` (state machine); `#13` is UX in `main.py`;
    `#14` is validation in `tests/`.
- **Phase 1.5 — 10 tickets opened 2026-06-08** (#29–#38). Extensions
  that make rep counting *better* — per-rep depth/timing/asymmetry,
  calibration, multi-exercise, real-clip regression set, replay
  viewer, A/B harness, set boundaries. Not required to close Phase 1
  but valuable for the Phase 4 dashboard and real-world use. One
  dependency flagged: #38 (set boundaries) needs #31 (timestamp-aware
  `RepCounter.update`).
- Phases 2–6 are not broken into tickets yet — do that when you get
  there.
- See `decisions.md` for design and process decisions (squash-merge
  default, no Co-Authored-By, branch naming, synthetic-first
  regression data, dep-free format module, signal-vs-pose separation,
  skip-on-None contract, trailing-buffer in synthetic clips, Phase
  1.5 as an extensions batch, etc.).
- Next action: merge PR #28 (hysteresis), then start Phase 1 (6/9)
  — depth gate (`#11`). Extends `RepCounter` with min-angle tracking
  in the down phase; only commit a rep on up-transition if min depth
  reached the gate (e.g. < 80°). Drives `partial_0reps` from 3 → 0
  and closes the regression set.

## Open questions

- Repo visibility is currently public — confirm long-term.
- Which exercises beyond squat / curl / deadlift matter? Affects Phase 3
  data collection.
- Single-user dashboard for now; multi-user is Phase 6.
