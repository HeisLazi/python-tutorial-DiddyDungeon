# Quest Lab friend onboarding

This branch ships the local-first Forge. It keeps the editor, shell and AI
terminal on the player’s machine; no private code or terminal session is sent
to the repository or to the public web page.

## Windows + WSL setup

Install Ubuntu in WSL and make sure `git`, `python3`, `python3-venv`, `npm` and
`node` are available inside Ubuntu. Then clone the repository and select the
Quest Lab branch:

```bash
git clone https://github.com/HeisLazi/python-tutorial-DiddyDungeon.git
cd python-tutorial-DiddyDungeon
git switch feature/cloud-sync-desktop
python3 -m venv .venv
.venv/bin/python -m pip install -r ide/server/requirements.txt
cd ide/frontend
npm install
cd ../..
```

The frontend install is deliberately local to the checkout. Do not reuse a
`node_modules` directory copied from a different operating system.

## Choose a quest workspace

The Forge platform checkout owns the canonical local player state. A quest
workspace is only the coding directory for Monaco and the two PTYs. A friend
can use the platform checkout as the workspace initially, or create a separate
worktree for a campaign project:

```bash
git fetch --all
git worktree add ../questlab-blackjack feature/quest-lab-ide
```

Never create or edit a second live save in the workspace. A workspace
`progress.json`, if present, is legacy evidence; use `questlab-state` or the
Forge state service for progression changes.

## Launch from Windows

From PowerShell in the cloned checkout:

```powershell
.\tools\questlab-launch.ps1 -Workspace ..\questlab-blackjack
```

The launcher refuses an unexpected branch unless `-AllowOtherBranch` is
explicitly supplied, injects the canonical state path, keeps backend reload
off so PTYs survive ordinary use, and prints the checkout/workspace identity.
It refreshes the configured upstream ref and refuses a stale checkout by
default; use `-AllowStaleCheckout` only for an intentional offline session.
Use `-NoBrowser` when opening the URL yourself. Ports move forward if the
preferred port is busy; the footer reports the actual checkout and marks a
checkout stale when the runtime health report sees commits behind upstream.
If `progress.json` has local player-state changes, the launcher warns but does
not overwrite them.

## Health checks

With Forge running, the shell PTY can inspect the same backend that powers the
UI:

```bash
questlab-state runtime
questlab-state authority
questlab-state campaign
```

`runtime` reports the repo branch, workspace branch, canonical state path,
legacy path, expected branch, upstream SHA/freshness and available CLI
commands. `authority` reports the canonical revision. `campaign` is the
player-facing projection. These are read-only reports; they do not edit a save.

On a Linux filesystem, keep the executable bit on `questlab-state`; a clone
that reports `Permission denied` should run `chmod +x questlab-state` once.

## Offline and account sync

Forge remains usable without cloud configuration. When account sync is enabled,
sign in separately on each device and resolve any explicit conflict banner by
choosing the validated cloud copy or this device’s copy. Do not copy
`progress.json` between devices by hand. The local gateway performs the
compare-and-swap update and increments the canonical revision.

The browser’s recoverable sync metadata (device identity, friendly label,
cursor and offline outbox) is partitioned by an opaque checkout namespace supplied by the local
runtime. This keeps two same-origin checkouts from sharing a mailbox while
keeping filesystem paths out of cloud/device records. Older unscoped browser
keys are left untouched and are not silently attributed to a new checkout.

The current branch does not expose PTYs, local files or AI credentials to a
public web deployment. Friends/presence, hosted dungeon scores and weekly raid
combat remain intentionally deferred until authenticated provider verdicts and
two-device sync acceptance are complete.
