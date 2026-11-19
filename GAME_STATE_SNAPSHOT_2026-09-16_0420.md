# Quest Lab game snapshot — 2026-09-16 04:20 (+02)

This is a read-only capture of the current local player projection before the
next roadmap slice. No save, legacy evidence file, PTY, browser runtime, or
hosted project was changed while taking it.

## Repository and custody

- Branch: `feature/cloud-sync-desktop`
- HEAD and `origin/feature/cloud-sync-desktop`: `788634717e6c5f34193843fad3acd3cbb6467eac`
- Canonical local authority: `/home/lazi/projects/python-tutorial-DiddyDungeon/progress.json`
- Legacy evidence only: `/home/lazi/projects/questlab-blackjack/progress.json`
- Canonical revision: `2`
- Canonical device id: `local-forge`
- Windows worktree boundary: `progress.json` and untracked `tutor.py` have real
  user-owned changes and were not staged, overwritten, or reconciled in this
  pass. Other apparent modified files in a WSL Git view are CRLF/LF checkout
  noise; Windows `git diff --ignore-space-at-eol` leaves only `progress.json`
  as a real tracked content diff.

## Canonical campaign projection

- Player: Level `2`, `50/100` current XP, `150` lifetime XP, `55` coins
- Vitality: `100/100` HP, `2` potions
- Streak: current `1`; sessions `1`; explanations `3`
- Blackjack project progress: `38%`
- Defeated mobs: `3` — The Empty Table, The Dealer's Hand, The Count Keeper
- Active encounter: The Hitman (Mob 3), Resolve `8/8`, zero applied Impact
- Achievement: First Blood
- Codex: `3` encounter records
- Equipment: Apprentice Coat; trinket None
- Companion: PYR / Tiny Code-Flame
- Canonical state events: `2` reconciliation events

## Legacy evidence comparison

The non-authoritative WSL legacy file was read without modification. It reports
Level `2`, `50` current XP, `55` coins, `3` defeated mobs and `38%` Blackjack
progress, matching the supported reconciliation fields. Its metadata has no
canonical revision, so it remains evidence only and cannot become a second
live save. No timestamp merge or direct copy was performed.

## Runtime and verification boundary

The user-visible long-lived port `5174` still serves the old Level 1 shell and
legacy `{shell, python, commands}` runtime response. It is documented as F-025
stale-runtime evidence and was not restarted so the existing PTY sessions stay
intact. The exact pushed source was separately checked in a clean ext4
disposable pair at backend `7351` / frontend `5186`: paired preflight passed,
the SVG HUD icons were visible, both PTY labels were `CONNECTED`, and a
gateway learning-event mutation advanced revision `0→1` in the same browser
without refresh. The disposable pair was stopped and removed.

## Current gates

- WSL backend suite: `77/77`
- Frontend suite: `33/33`
- Windows Vite production build: successful, `1,345` modules transformed
- Browser method: in-app browser K&M only; no Playwright
- Claude availability heartbeat: active for `04:23` review window
- Hosted Supabase/device migration, real two-device sync, avatar, Tauri,
  public web and Slice 8 remain explicit approval-gated roadmap work.
