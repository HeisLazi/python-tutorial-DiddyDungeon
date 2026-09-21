# Quest Lab game-state snapshot — 2026-09-16 07:38

## Protected canonical state

- Checkout: `feature/cloud-sync-desktop`
- Code tip before this documentation checkpoint: `238d4ebed4ac02d8f863a85f8155cb601dd78e0a`
- Canonical path: repository `progress.json` (protected; not staged)
- Canonical SHA-256 after the earlier bounded cleanup: `5618f9dd9ae2fc0724056ea08448e1736479772b59ada949bec08b5340fbd6f0`
- Canonical revision: `5`
- Player: Level `2`, `50 / 100` XP, `150` lifetime XP, `55` coins, `100 / 100` HP
- Blackjack: 3 cleared mobs; `The Hitman` active at `8 / 8` Resolve; 38% project progress
- Codex: 3 validated legacy encounter records
- No equipment, companion, mastery/shield, interview or unsupported reward history was inferred by the reconciliation

The protected hash and revision were unchanged by the isolated browser check below.

## Isolated live-projection acceptance

A disposable WSL workspace and an explicitly confirmed local state cache were
created through `--use-local-state --confirm-local-state`; the source snapshot
was copied atomically by the custody service. The new
`questlab-km-preflight.ps1 -RequireIsolatedState` gate passed after its
Windows/WSL separator bug was corrected. The browser was operated only with
CUA click/type/scroll/observation; no refresh and no Playwright were used.

1. Initial isolated projection matched the protected snapshot: Level 2,
   50 XP, 55 coins, The Hitman 8/8, 3 cleared mobs and 3 Codex records.
2. A trusted in-process state-service objective (`choice_flow`) advanced the
   isolated revision 5→6 and changed Resolve 8/8→4/8 live. Forge displayed
   `OBJECTIVE VERIFIED` while the shell and AI PTY labels remained `CONNECTED`.
3. A second trusted objective (`stop_condition`) advanced revision 6→7. The
   state service awarded its own validated `+30 XP / +15 coins`, defeated The
   Hitman, unlocked The Bust Hound and grew the Codex record. Without a
   browser refresh, the UI showed Level 2, 80/100 XP, 70 coins, 4 cleared mobs,
   The Bust Hound at 7/7 Resolve, the defeated Hitman evidence, and the same
   connected PTYs across Forge, Journal, Codex, Character and Homestead.
4. The HUD screenshot showed the heart, coin and flame SVG icons with no nested
   empty pills; the direct-child selector contract and PowerShell parse both
   passed.

The disposable runtime, tab, workspace and local cache were stopped/removed
after the check. No protected JSON or Campaign `tutor.py` file was edited by
this run.

## Remaining gates

The local authority/revision/event/projection slice is green. A real second
Windows machine and the explicit F-039 tracked-save custody decision are still
needed for the final local-distribution gate. Hosted Supabase sync/avatar,
Tauri packaging, public routes and social features remain approval-gated and
were not started.
