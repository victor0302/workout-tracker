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

- `vision/` — three clearly-separated concerns:
  - **Inference** — `pose_estimator.py` (MediaPipe wrapper, needs
    `cv2` + `mediapipe` + `numpy`).
  - **Signal extraction & filtering** — `signal.py` (dep-free Python:
    `joint_angle`, `knee_angle`, plus smoothing/hysteresis/depth-gate
    as Phase 1 lands them).
  - **State machine** — `rep_counter.py` (dep-free dataclass; consumes
    a numeric signal, doesn't know where it came from).
  - Also: `recording.py` (dep-free `Keypoint` + `build_record` for the
    JSONL format), `main.py` (capture loop), `replay.py` (headless
    replay), `exercise_classifier.py` (stub).
  - Entry points:
    - `python -m vision.main --source 0` — live capture
    - `python -m vision.main --source 0 --record clip.jsonl` — capture + record
    - `python -m vision.replay clip.jsonl` — headless replay
  - **Import rule:** tests and scripts should import from `signal` or
    `recording` (both dep-free), not from `pose_estimator` or `main`,
    to avoid pulling cv2 / mediapipe / numpy.
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
- **Phase 1 in flight** — 4/9 merged on main, `#10` open in PR #28:
  - `#6` (PR #21) — record-and-replay harness
  - `#7` (PR #22) — synthetic regression set
  - `#8` (PR #24) — averaged knee angle in `vision/signal.py`
  - `#9` (PR #26) — EMA + median smoothing (`Smoother` Protocol);
    side effect: `jitter_0reps` dropped 14 → 0
  - `#10` (PR #28, **in flight**) — hysteresis on `RepCounter`,
    `dwell_frames=5`. Required adding a 15-frame trailing buffer to
    every synthetic clip; counts unchanged after that.
- Remaining Phase 1: `#11` depth gate → `#12` min-duration →
  `#13` debug overlay → `#14` regression test.
- Only `partial_0reps` still fails the counter (3 vs expected 0).
  `#11` will close that.
- **Phase 1.5** — 10 extension tickets opened 2026-06-08 (`#29`–`#38`).
  Per-rep depth/tempo/asymmetry, calibration, multi-exercise, replay
  viewer, A/B harness, set boundaries, real-clip regression set. Not
  required to close Phase 1 — see `decisions.md` for the rationale.
- Phases 2–6 are described in `notes.md` but not yet broken into
  tickets.

## When working on Phase 1

The foundation is now on main:
- `vision/replay.py` runs a JSONL clip through the rep counter headless
- `regression_set/*.jsonl` is the labeled test set
- `vision/signal.py` handles per-sample signal extraction + filtering
  (`knee_angle`, `EMASmoother`, `MedianSmoother`)
- `vision/rep_counter.py` handles state-machine behavior over a stream
  of samples

The remaining work (`#10`–`#14`) tunes the rep counter against the
regression set. **Don't tune thresholds in isolation.** Every change
to `vision/signal.py` or `vision/rep_counter.py` should be validated
by replaying the regression set. If you find yourself adjusting
threshold constants without checking
`python -m vision.replay regression_set/*.jsonl` outputs, stop. The
regression test in `#14` will formalize this.

**Where each remaining ticket lives:**
- `#11` depth gate, `#12` min-duration → extend `RepCounter`. They
  change *when* the counter transitions given a stream of samples —
  that's state-machine behavior, not signal transformation. `#10`
  (hysteresis) is the template; PR #28 has the pattern.
- `#13` debug overlay → `main.py` (UX only).
- `#14` regression test → `tests/`.

**Synthetic clip trailing buffer.** Every clip in `regression_set/`
ends with a 15-frame trailing buffer of standing pose. If you add a
new state-machine filter that needs more post-event evidence than
that (`#12`'s min-duration with default 0.8s = 24 frames might be one
example), extend `_with_trailing_buffer`'s default in
`scripts/gen_synthetic_clips.py` and regenerate.

**Phase 1.5 batch.** Don't mix Phase 1 and Phase 1.5 work in the same
PR — the batches have different closure conditions and Phase 1.5 can
be skipped entirely if priorities shift to Phase 2/3/4.

Per-sample filters (the kind `signal.py` houses) implement the
`Smoother` Protocol: `update(x: float | None) -> float | None` plus
`reset()`. `update(None)` returns `None` without mutating state — no
interpolation, no last-known-value substitution. Any new filter must
follow this contract.

Synthetic clips today exercise every Phase 1 failure mode. After `#9`
only `partial_0reps` still fails; `#11` (depth gate) is what closes
it. `#10` and `#12` are belt-and-suspenders against jitter patterns
the synthetic set doesn't cover specifically.
