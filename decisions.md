# Decisions

Running log of design and process decisions that aren't obvious from
code or git history. Newest at the top.

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
