# Decisions

Running log of design and process decisions that aren't obvious from
code or git history. Newest at the top.

## 2026-06-12 — Phase 1 Hardening is its own batch; auth/CORS deferred to Phase 4

A health/security audit of the Phase 1 codebase produced six tickets
(`#40`–`#45`, titled `Phase 1 Hardening (n/6): ...`) covering: GitHub
Actions CI, ruff + pre-commit, mypy, pinned deps + Dependabot,
NaN/Inf guards on `RepCounter`/`Smoother` inputs, JSONL clip format
versioning + robust parse errors. The audit also flagged the dashboard
having no auth and no CORS — anyone reachable on the port can POST to
`/ingest/*` and read `/metrics`.

**Why a separate batch from Phase 1.5.**
1.5 is feature extensions to rep counting (per-rep metrics,
calibration, multi-exercise). Hardening is engineering rigor
(tooling, robustness, supply-chain). Different reviewers might pick
them up; different urgency tradeoffs. Keeping them in separate
labeled batches lets the user prioritize independently and merge them
out of order without confusion about "which Phase 1 batch is this from?"

**Why auth/CORS isn't in this batch.**
The dashboard is the only component with that exposure, and the
dashboard's full hardening (auth, CORS, rate limiting, input bounds
on Pydantic models) is Phase 4 work. Pulling it into Phase 1
Hardening would muddle the scope — Phase 1 Hardening's job is the
vision-side codebase and the build/CI tooling that serves all phases.

**Carry forward.**
- Branch naming: `phase1-hardening/NN-slug` (analogous to
  `phase1.5/NN-slug`). Don't mix Phase 1, Phase 1.5, and Hardening
  work in one PR.
- Suggested merge order: #40 (CI) first to unlock enforceability of
  #41/#42/#43, then lint+types, then deps, then the code-side
  hardening (#44, #45) in parallel.
- Future audits of later phases follow the same pattern: open a
  `Phase N Hardening` batch with whatever tickets the audit produces.
- Dashboard auth/CORS captured as a Phase 4 must-do in `notes.md`;
  ticket it when Phase 4 starts.

## 2026-06-08 — Phase 1.5 is a distinct batch for rep-counter extensions

Phase 1 (`#6`–`#14`) ships "rep counting that works." A second batch
of 10 tickets (`#29`–`#38`, titled `Phase 1.5 (n/10): ...`) extends
the same problem space — per-rep depth/tempo/asymmetry, calibration,
multi-exercise support, real-clip regression set, replay viewer, A/B
harness, set boundaries.

**Why a separate label, not just continuing the Phase 1 numbering.**
Original Phase 1 has a clear closure condition: when `#14` lands and
the regression set goes green, rep counting is "done" in the sense of
the original ticket. Phase 1.5 work makes it *better* (more metrics,
calibrated thresholds, multi-exercise) but isn't required to close
that phase. Keeping them in a separate batch lets Phase 1 end cleanly
on `#14` without an implicit "but we still have nine more rep-counter
PRs to ship" overhang. It also lets the user prioritize: skip the
1.5 batch entirely if they want to jump to Phase 2/3/4 first.

**Carry forward.**
- Branch names: `phase1.5/NN-slug`. Numeric prefix sorts in ticket
  order within the batch.
- The same "extends, doesn't replace" pattern is available for any
  future phase that needs follow-on work without inflating the
  original scope. Call it `Phase N.5` and link from `notes.md`.
- Don't mix Phase 1 and Phase 1.5 work in one PR.

## 2026-06-08 — Synthetic regression clips need a trailing buffer

Every clip in `regression_set/` ends with ~0.5s (15 frames) of
holding at standing-pose angle (170°).

**Why.** Sanity-checking `#10` (hysteresis, dwell=5) revealed every
counted clip lost its last rep — the clip ended mid-up-transition,
with only ~3 frames above 160° before EOF, but dwell=5 needs five
consecutive frames past the threshold to commit. Real recordings
have post-rep trailing time naturally (the person stays in frame
after the last rep); the synthesis needed to mirror that.

The fix lives in `scripts/gen_synthetic_clips.py` as
`_with_trailing_buffer(records, frames=15, angle=170°)` applied to
every clip in `CLIPS`.

**Carry forward.**
- Any new synthetic clip applies `_with_trailing_buffer` before
  writing.
- When adding a new state-machine filter that needs longer post-event
  evidence (`#12` min-duration, future longer dwell tunings), check
  the trailing buffer is still long enough. Extend the helper's
  default rather than tweaking individual clips.
- Real-clip captures (Phase 1.5 (1/10), `#29`) should include a few
  seconds of standing time at the end, same reason.

## 2026-06-07 — Three-way split: inference / signal / state machine

`vision/pose_estimator.py` is strictly a MediaPipe wrapper — inference
only, no analysis. `vision/signal.py` does per-sample signal
extraction and filtering (`joint_angle`, `knee_angle`, smoothers).
`vision/rep_counter.py` is a state machine over a stream of numeric
samples; it doesn't know where the signal came from.

**Why.** Three concerns separated cleanly:
1. inference (`pose_estimator`, needs mediapipe + numpy + cv2),
2. signal extraction and filtering (`signal`, dep-free Python),
3. state machine over samples (`rep_counter`, dep-free dataclass).

Tests and tooling can import `signal` without dragging the inference
stack.

**Where the remaining Phase 1 tickets land:**
- `#9` smoothing → `signal.py` (per-sample transformation). ✅ Done.
- `#10` hysteresis → `rep_counter.py` (when to commit a state
  transition is state-machine behavior).
- `#11` depth gate → `rep_counter.py` (track min angle in down phase;
  gate at up transition).
- `#12` min-duration → `rep_counter.py` (timestamps on transitions).
- `#13` debug overlay → `main.py` (UX).
- `#14` regression test → `tests/`.

Rule of thumb: if it transforms a sample, it's `signal.py`. If it
changes *when the rep counter transitions* given a stream of samples,
it's `rep_counter.py`. (An earlier version of this entry incorrectly
lumped `#10–#12` into `signal.py` — fixed 2026-06-07.)

## 2026-06-07 — `Smoother` Protocol for filters in `signal.py`

Per-sample filters in `signal.py` implement a small Protocol:

    class Smoother(Protocol):
        def update(self, x: float | None) -> float | None: ...
        def reset(self) -> None: ...

Two implementations today: `EMASmoother(alpha=0.3)` and
`MedianSmoother(window=5)`. `vision.main` and `vision.replay` both
take a `Smoother` and pipe `knee_angle(...)` through it.

**Why.** Makes filters interchangeable from the call site, encodes
the skip-on-`None` contract in the type signature, and lets future
filters slot in (Kalman, Savitzky–Golay, whatever) without rewiring
callers.

**Carry forward.** Any new per-sample filter in `signal.py` implements
`Smoother`. `update(None)` returns `None` without mutating state.
Expose `reset()` for tests and for cases where the caller knows the
signal has discontinuously restarted (e.g. new session).

## 2026-06-07 — Skip-on-`None` contract for the signal pipeline

When `knee_angle` can't produce a value (low visibility, missing
landmarks), it returns `None` and the caller skips the frame — no
interpolation, no last-known-value substitution, no rep counter
update.

**Why.** Interpolating across missing frames would fabricate signal
the counter then acts on. Better to drop the frame and let real
samples drive the state machine.

**Carry forward.** Smoothing and hysteresis additions in `signal.py`
must propagate `None` cleanly: a smoother fed `None` should also emit
`None` (or skip the sample from its window), never substitute. Same
for any future filter.

## 2026-06-06 — Regression-clip filenames encode expected rep count

Clips in `regression_set/` are named `<label>_<n>reps.jsonl`. The `#14`
regression test parses the integer before `reps` as the expected count
for that clip.

**Why.** Test data is self-describing. No sidecar metadata file to
keep in sync with the clips; renaming or adding clips needs no other
edits.

**Carry forward.** Any new regression clip — synthetic or real — must
follow this convention. If we later need extra labels (e.g. exercise
type), append fields: `<label>_<n>reps_<exercise>.jsonl`.

## 2026-06-06 — Synthetic regression set first; real clips augment later

Phase 1's regression set started as seven seeded synthetic clips, not
human-recorded footage.

**Why.** Synthetic clips unblocked `#8–#14` immediately without
requiring the user to perform squats on camera. They also exercise
specific failure modes (`partial_0reps.jsonl` for the depth gate,
`jitter_0reps.jsonl` for hysteresis) more precisely than real footage
would. Real clips can be added under the same naming convention later
as a complement.

**Carry forward.** For future phases that need test data, prefer
seeded programmatic generation when it cleanly hits the failure modes
under test. Real captures are a complement, not a substitute.

## 2026-06-06 — Dep-free `vision/recording.py` for the JSONL format

`Keypoint` and `build_record` live in `vision/recording.py` — a tiny
module with no `cv2`, `mediapipe`, or `numpy` imports. Runtime modules
(`pose_estimator`, `main`, `replay`), the synthesis script, and tests
all import from it.

**Why.** The synthetic-clip generator needs to write the JSONL format
but doesn't need any heavy runtime deps. Leaving `Keypoint` /
`build_record` in `pose_estimator.py` (which imports MediaPipe) or
`main.py` (cv2) would force every tooling script and test environment
to install the full runtime stack.

**Carry forward.** When adding tooling or tests that need a shared
data shape, prefer factoring it into a dep-free submodule over
importing from a runtime entry point. Rule of thumb: if a script only
needs the *shape* of something, the shape should live in a module
that doesn't pull frameworks.

## 2026-06-04 — Phase 0 acceptance encoded as pytest tests, not runbook steps

Every Phase 0 ticket's acceptance was converted from a manual
smoke-test step into an automated pytest test under `tests/`, with one
exception (#4) where actual hardware was required.

**Why.** Manual smoke tests rot — nobody re-runs them. Pytest tests
become permanent regression coverage at small cost (one focused file
per ticket, plus `pytest` + `httpx` in `requirements.txt`).

**What we couldn't automate.** Phase 0 (4/5) — "OpenCV window shows
pose landmarks rendered on you" needs a real webcam and MediaPipe
inference. We covered the *contract* between vision and the dashboard
automatically; the hardware step stays a manual check in the PR test
plan.

**Carry forward.** Default approach for future phases: if a ticket's
acceptance can be expressed as a test, write the test. Hardware-only
acceptance stays in the PR test plan as a checklist item.

## 2026-06-04 — Squash merge for all PRs

All Phase 0 PRs squash-merged with `--delete-branch`. Linear history on
main, one commit per ticket.

**Why.** Each PR was a single focused change. Squash gives clean
per-ticket attribution and an easy `git revert` boundary. Rebase
merging would have surfaced our identical `tests/conftest.py` adds
across PRs #17–#19 as conflicts; squash sidesteps that.

**Carry forward.** `gh pr merge N --squash --delete-branch` is the
default merge command.

## 2026-06-04 — No `Co-Authored-By: Claude` trailer on any commit or PR

User preference. All work originates from the user; Claude's
involvement is not recorded in git metadata.

**Carry forward.** Do not add the `Co-Authored-By: Claude` trailer
that Claude Code's default workflow suggests. Do not add "Generated
with Claude Code" footers to PR bodies.

## 2026-06-04 — Branch naming convention: `phaseN/MM-slug`

Phase 0 used `phase0/01-env-check`, `phase0/02-dashboard-boot`, etc.

**Why.** Phase is obvious in `git branch -a` and `gh pr list`. Numeric
prefix sorts the same as ticket order.

**Carry forward.** Phase 1 branches will be `phase1/01-...` through
`phase1/09-...`. Docs/process branches go under `docs/<slug>`.
