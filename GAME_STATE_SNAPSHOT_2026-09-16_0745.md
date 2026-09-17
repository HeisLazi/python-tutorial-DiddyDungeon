# Quest Lab game-state snapshot — 2026-09-16 07:45 +02

This is the authoritative checkpoint before the next roadmap slice.

## Repository and custody

- Branch: `feature/cloud-sync-desktop`
- Local HEAD and `origin/feature/cloud-sync-desktop`: `0397e2d71e202b62ffbfb59ae733848f84997241`
- Canonical state: repository `progress.json`; SHA-256
  `5618f9dd9ae2fc0724056ea08448e1736479772b59ada949bec08b5340fbd6f0`
- Canonical state is revision `5`; no Forge runtime is currently running from
  this checkout.
- `progress.json` is a user-modified protected file and root `tutor.py` is an
  untracked Campaign notebook; neither is staged or overwritten.
- Legacy workspace evidence remains non-authoritative and is not edited.

## Canonical campaign projection

- Player: Level `2`, `50 / 100` current XP, `150` lifetime XP, `55` coins,
  `100 / 100` HP
- Blackjack: 38% project progress; defeated **The Empty Table**, **The
  Dealer's Hand** and **The Count Keeper**
- Active encounter: **The Hitman**, Resolve `8 / 8`
- Codex: 3 validated encounter records
- Achievement: First Blood
- Equipment: Apprentice Coat; no trinket; companion PYR level 1/bond 0
- Reconciliation still records `reward_history_inferred: false`; unsupported
  equipment, mastery, interview and reward details remain un-inferred.

## Prior verification carried forward

The 07:38 disposable isolated-cache CUA run (documented in the prior snapshot)
verified revision-aware live updates across HUD, Journal, Codex, Character and
Homestead, plus stable shell/AI PTYs. A separate workspace alone is no longer
considered sufficient for a mutating browser check; future disposable mutation
must pass `questlab-km-preflight.ps1 -RequireIsolatedState`.

## Next gate

The local authority/projection implementation is green. The next unblocked
work is a bounded local hardening/review slice; final local-distribution proof
still needs a real second-Windows environment and the explicit F-039 custody
decision. Hosted Supabase sync/avatar, Tauri, public and social work remain
approval-gated.
