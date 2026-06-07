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
  joint-angle signal), exercise classifier (currently a stub), JSONL
  record/replay harness. Entry points:
  - `python -m vision.main --source 0` — live capture
  - `python -m vision.main --source 0 --record clip.jsonl` — capture + record
  - `python -m vision.replay clip.jsonl` — headless replay
  - `vision/recording.py` — dep-free `Keypoint` + `build_record`; the
    canonical source for the JSONL format. Import from here in tests
    and scripts to avoid pulling cv2 / mediapipe / numpy.
- `firmware/esp32_max30102/` — Arduino sketch. Reads MAX30102 over I2C,
  broadcasts a JSON payload via a single BLE notify characteristic. HR
  works; SpO2 algorithm is stubbed.
- `ble_listener/` — `bleak` client. Scans for `WorkoutBand`, subscribes
  to the characteristic, forwards each JSON sample to the dashboard.
- `dashboard/` — FastAPI. `POST /ingest/vision`, `POST /ingest/biometric`,
  `GET /metrics`, `GET /metrics/history`. State is in-memory; no
  persistence yet (that's Phase 4).
- `regression_set/` — labeled JSONL clips for the Phase 1 rep counter
  regression test (`#14`). Synthetic baseline today; real clips can
  augment later. Filename convention: `<label>_<n>reps.jsonl` — the
  integer before `reps` is the expected count.
- `scripts/` — offline tooling:
  - `check_env.py` — Phase 0 import / webcam smoke test
  - `gen_synthetic_clips.py` — deterministically regenerates
    `regression_set/`

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

- Scaffold and **Phase 0 complete** (2026-06-04).
- **Phase 1 in flight** — 2/9 merged 2026-06-06:
  - `#6` (PR #21) — record-and-replay harness
  - `#7` (PR #22) — synthetic regression set
- Next ticket: `#8` (averaged left+right knee angle). Then `#9`–`#14`
  in order.
- Phases 2–6 are described in `notes.md` but not yet broken into
  tickets.

## When working on Phase 1

The foundation is now on main:
- `vision/replay.py` runs a JSONL clip through the rep counter headless
- `regression_set/*.jsonl` is the labeled test set

The remaining Phase 1 work (`#8`–`#14`) tunes the rep counter against
that set. **Don't tune thresholds in isolation.** Every change to
`vision/rep_counter.py` or the signal pipeline in `vision/main.py`
should be validated by replaying the regression set. If you find
yourself adjusting threshold constants without checking
`python -m vision.replay regression_set/*.jsonl` outputs, stop. The
regression test in `#14` will formalize this.

Synthetic clips today expose every Phase 1 failure mode the tickets
address. `partial_0reps.jsonl` and `jitter_0reps.jsonl` intentionally
fail the naive counter — driving them to 0 is the work.
