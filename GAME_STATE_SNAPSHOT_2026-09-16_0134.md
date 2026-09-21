# Forge game snapshot — 2026-09-16 01:34 +02:00

This is a read-only checkpoint captured before the roadmap-wide Claude plan.
No state file, legacy evidence, PTY, browser tab or hosted provider was
changed while taking the snapshot.

## Source boundary

- Branch: `feature/cloud-sync-desktop`
- Pushed HEAD: `4a494b5` (`docs: record final live projection smoke`)
- Working-tree changes intentionally preserved: modified player
  `progress.json` and untracked Campaign `tutor.py`; neither is staged.
- The canonical local cache observed here is the repository-root
  `progress.json`, through the Quest Lab state service. A workspace
  `progress.json` remains legacy/non-authoritative evidence.

## Canonical campaign state observed

- Revision `2`, Level `2`, current XP `50 / 100`, lifetime XP `150`;
- HP `100 / 100`, coins `55`;
- Blackjack progress `38%`;
- Defeated: The Empty Table, The Dealer's Hand and The Count Keeper;
- Active encounter: The Hitman, Resolve `8 / 8`;
- Next allowed mob: The Bust Hound remains locked until The Hitman is cleared;
- Codex encounter records: 3 (the three cleared mobs);
- State events: 2, both validated `reconcile_legacy_progress` events;
- Achievement evidence: First Blood;
- Equipment/title: no equipment, trinket or title was inferred in the
  reconciled state;
- Companion: starter PYR projection; no unsupported evolution was inferred;
- Mastery/shields/interview completion: not inferred.

## Runtime custody observed

The long-lived local runtimes were left untouched:

- older Forge: frontend `5173` / backend `7332`;
- current Forge: frontend `5174` / backend `7333`;
- the disposable verification runtime from the previous checkpoint was
  already stopped and removed.

## Existing verification baseline

- WSL backend suite: 69 tests passed;
- frontend suite: 31 tests passed;
- Windows Vite build: 1,345 modules transformed;
- final disposable K&M smoke: live reward revision polling, HUD/Quest
  Journal/Codex/Character/Homestead coherence and both `CONNECTED` PTYs;
- browser interaction policy: click, scroll and type only; no Playwright;
- remaining roadmap gates: provider-authenticated adjudication, hosted
  two-device state/avatar transport, custody approval, Windows/Tauri proof,
  safe web surface, and the upstream/reviewer Monaco/DOMPurify remediation
  gate. The current 0.56.0 risk is explicitly accepted; 0.53.0 was rejected
  after inspecting its older vendored 3.1.7 sanitizer.

This snapshot is evidence for planning only. It is not a migration approval,
cloud seed, merge of legacy files, or completion claim for the roadmap.
