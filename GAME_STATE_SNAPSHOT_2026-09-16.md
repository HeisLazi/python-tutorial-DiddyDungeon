# Forge game snapshot — 2026-09-16

This is a persistent, read-only checkpoint for the ongoing roadmap pass. It
does not mutate the player save, migrate custody, seed Supabase or restart any
runtime.

## Source and working-tree boundary

- Branch: `feature/cloud-sync-desktop`
- Snapshot source commit before this document: `6c61317`
- The only intentional working-tree state is the player's modified
  `progress.json` and untracked Campaign `tutor.py`; neither is staged or
  included in any friend bundle.
- The visible long-lived runtimes/PTYs were not restarted. A stale older
  runtime may still show starter values; fresh launches must use the guarded
  launcher on this branch.

## Canonical local state (read-only observation)

The state gateway canonical cache reports:

- revision 2;
- Level 2, 50 / 100 XP, 150 lifetime XP and 55 coins;
- three defeated Blackjack mobs, 38% Blackjack project progress and The Hitman
  as the current encounter;
- three Codex encounter records and two reconciliation state events;
- no unsupported equipment, mastery, companion evolution or interview reward
  was inferred.

The quest workspace `progress.json` remains legacy/non-authoritative evidence.
The state service is the only progression writer; direct workspace edits do not
increment the canonical revision or enter the event/cloud projection.

## Verified implementation state

- Campaign, Codex, Character, Homestead, Quest Journal, Dungeon and Practice
  project from the shared revision/event source.
- React owns the five monochrome SVG HUD icons; revision polling does not
  replace them with nested pills or emoji.
- Direct HUD stat pills reserve compact icon/value slots so initial sync and
  digit-length changes do not reflow the top bar.
- PYR Battle/Boss/Dungeon challenges are now partitioned by opaque per-tab
  session ids and looked up by nonce; a second tab cannot invalidate a pending
  answer in the first tab. Hosted provider authentication remains open.
- Campaign `tutor.py` remains a dedicated Campaign surface; Practice is
  separate and never writes it or Campaign/Dungeon rewards.
- Infinite Dungeon local loop is K&M-verified: fresh loadout, checkpoint,
  validated verdict, blank-on-rotation, progressive rooms, REST/MARKET,
  purchase and local leaderboard.
- `tools/questlab-package.ps1` now creates a committed-HEAD-only friend
  folder/ZIP and excludes dirty `progress.json`/untracked `tutor.py`.
- Fresh K&M projection acceptance also covered a validated reward, live
  Resolve reduction, mob defeat/next unlock, Codex growth, Homestead purchase,
  Campaign Tutor and Practice boundaries with both PTYs connected.

## Gates still open

- Real authenticated two-device Supabase player-state/avatar acceptance,
  provider-authenticated adjudication and hosted Dungeon persistence;
- non-OneDrive custody migration for the real save (still explicit opt-in);
- Windows friend-machine launch and a native Windows/Tauri desktop proof (the
  clean ext4 WSL clone/install/launch smoke is now verified);
- targeted frontend dependency decision (one low and one moderate
  Monaco/DOMPurify advisory; npm only offers a semver-major 0.53.0 downgrade,
  and no forced fix was applied);
- a disposable 0.53.0 Monaco candidate passed 31 frontend tests, a 1,293-
  module build and a zero-vulnerability production audit; adoption remains a
  compatibility decision; npm audit does not inspect Monaco's vendored
  sanitizer bundle;
- safe web/Vercel account/profile surface and, only after those gates, any
  friends/presence/raid transport.

## Automated evidence at snapshot time

- WSL backend: 69 tests passed;
- frontend: 31 tests passed;
- Windows Vite production build: 1,345 modules transformed;
- Python compilation and PowerShell launcher/package parsing passed;
- browser verification used K&M click/scroll/type only; no Playwright.

See `ROADMAP_EXECUTION_PLAN.md`, `AGENT_CLOUD_DESKTOP_HANDOFF.md` and
`FORGE_ROADMAP_ISSUES_LOG.md` for the dependency-ordered plan and acceptance
boundaries.
