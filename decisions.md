# Decisions

Running log of design and process decisions that aren't obvious from
code or git history. Newest at the top.

## 2026-06-07 — `vision/signal.py` houses all rep-counter signal processing

`joint_angle`, `knee_angle`, and (going forward) smoothing,
hysteresis, depth-gate logic etc. all live in `vision/signal.py`.
`vision/pose_estimator.py` is now strictly a MediaPipe wrapper —
inference only, no analysis. `vision/rep_counter.py` is a state
machine that consumes a numeric signal; it doesn't know where the
signal came from.

**Why.** Three concerns separated cleanly:
1. inference (`pose_estimator`, needs mediapipe + numpy + cv2),
2. signal extraction and filtering (`signal`, dep-free Python),
3. state machine (`rep_counter`, dep-free dataclass).

Tests and tooling can import `signal` without dragging the inference
stack. Future Phase 1 work (`#9–#12`) extends `signal.py` without
touching `main.py` or `rep_counter.py`.

**Carry forward.** Smoothing (`#9`), hysteresis (`#10`), depth gate
(`#11`), min-duration filter (`#12`) all land in `vision/signal.py`.
Do not put signal-processing back into `pose_estimator.py`,
`rep_counter.py`, or `main.py`. The rep counter stays a pure state
machine.

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
