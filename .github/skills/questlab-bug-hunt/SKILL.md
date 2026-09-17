---
name: questlab-bug-hunt
description: Run a browser-first end-to-end bug hunt for Quest Lab/Forge. Use this whenever the user asks for a full E2E pass, bug bash, visual QA, regression hunt, click-through test, or independent reviewer comparison. Preserve protected saves, legacy evidence, Campaign tutor.py, and long-lived PTYs; use an isolated disposable state/runtime, no Playwright, and record every confirmed bug with reproducible evidence and a fair reviewer score.
compatibility: Requires PowerShell + WSL, the Quest Lab guarded launcher/preflight, and browser K&M automation. Claude/Copilot review CLIs are optional; never grant read-only reviewers write access to the checkout.
---

# Quest Lab bug hunt

Use this skill to find regressions that ordinary unit tests miss while keeping
the player's state and existing sessions safe.

## Safety boundary

- Read the current branch, issue ledger and handoff before testing.
- Treat the repository `progress.json`, legacy/workspace evidence, and root
  `tutor.py` as protected user data. Never reset, merge, stage, or overwrite
  them.
- Never kill or restart a pre-existing Forge/backend/frontend process or shell/
  AI PTY. Start the test on unused ports with an explicitly isolated cache.
- Use only browser click, scroll, type, accessibility inspection and screenshots
  for UI acceptance. Do not use Playwright or DOM scripting to drive the app.
- Reviewers are read-only. They may inspect source, tests and persistent logs,
  but may not edit files, run destructive commands, or claim hosted readiness.

## Run order

1. **Baseline and custody.** Record branch/HEAD/upstream, dirty protected
   paths, canonical/legacy identity, and the disposable state/workspace paths.
   Require the guarded preflight's isolated-state check before any mutation.
2. **Deterministic gates.** Run the applicable backend/frontend suites,
   compile/build checks and launcher/preflight checks. Record failures verbatim
   and rerun a transient failure once before classifying it.
3. **Launch and observe.** Start a disposable current-branch runtime in a
   built/normal-launch mode. Confirm checkout identity, canonical revision,
   HUD baseline, visible SVG icons, Campaign Tutor surface, Practice boundary,
   and both terminal labels.
4. **Walk every surface.** With K&M only, exercise HUD, Character, Homestead,
   Quest Journal, Codex, Campaign Tutor, Infinite Dungeon, Practice, Settings,
   resizing/compact HUD, search, notes, purchases, checkpoints, room rotation,
   death/new-run, and reconnect/revision polling. Trigger at least one valid
   state-gateway mutation and verify every projection updates without refresh or
   PTY remount. Do not reveal future questions/answers.
5. **Negative paths.** Try empty/oversized input, stale revisions/question IDs,
   unavailable providers, malformed projections, invalid purchases, duplicate
   clicks and navigation during syncing. Confirm clear errors, no reward
   invention, no cross-mode writes and no second authoritative save.
6. **Independent review.** Ask Claude and Copilot separately for read-only
   findings against the same commit and scope. Give each the same checklist and
   require issue IDs/evidence; do not show one reviewer's findings to the other
   before scoring.
7. **Log and score.** Append to a persistent `BUG_HUNT_LOG_YYYY-MM-DD.md`, not
   `/tmp`. Deduplicate against the issue ledger and within the run. A confirmed
   unique bug scores by impact: P0=8, P1=5, P2=3, P3=1. A reproducible visual
   or behavioral defect is still one bug; duplicates score zero. Add one bonus
   point for a minimal reproduction and subtract two for a false positive.
   Winner is highest total, with unique-bug count as the first tie-breaker.

## Finding format

Record every finding with:

```text
BUG-<date>-<number>
Reviewer: primary | Claude | Copilot
Severity: P0 | P1 | P2 | P3
Surface: HUD | Character | Homestead | Journal | Codex | Tutor | Dungeon | Practice | Settings | launcher | backend | packaging
Status: new | fixed during hunt | known/open | duplicate | false positive
Evidence: exact click/type sequence, visible result, endpoint/test output, and commit/runtime identity
Impact: what a learner loses or what invariant is broken
Score: 8/5/3/1, plus or minus any documented bonus/penalty
Owner/next action: precise repair or approval gate
```

Only call a bug confirmed when the evidence reproduces it in the disposable
runtime or an authoritative deterministic check. A reviewer may report a
possible issue, but the primary run must label it unverified rather than add a
point.

## Exit report

End with: baseline and commit, tests/gates, every confirmed bug sorted by
severity, fixed-vs-open status, reviewer scorecard, false positives/duplicates,
protected-file/runtime custody, and the exact remaining infrastructure gates.
