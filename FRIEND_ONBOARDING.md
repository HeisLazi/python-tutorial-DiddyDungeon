# Quest Lab friend onboarding

This branch ships the local-first Forge. It keeps the editor, shell and AI
terminal on the player’s machine; no private code or terminal session is sent
to the repository or to the public web page.

## Windows + WSL setup

Install Ubuntu in WSL and make sure `git`, `python3`, `python3-venv`, `npm` and
`node` are available inside Ubuntu. Prefer cloning inside Ubuntu's Linux
filesystem (for example `~/projects`) rather than under a OneDrive-mounted
`/mnt/c` path; native dependency installs are reliable there. Then clone the
repository and select the Quest Lab branch:

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
`node_modules` directory copied from a different operating system. Never run
`npm install` or `npm ci` against the live OneDrive-mounted
`ide/frontend/node_modules` from WSL; use a disposable ext4/Linux checkout when
repairing dependencies. When the launcher runs under WSL it checks that this
install contains a native Linux Rollup optional package and exits before
starting Forge if that check fails.

## macOS native setup (target; not yet certified)

Quest Lab can run natively on macOS through the same Python/FastAPI and Vite
launcher used by native Linux. This is a local-first path; no WSL layer or
desktop wrapper is required. Install Git, Python 3.11+ and Node.js 20+ (Homebrew
is optional), then use a normal local filesystem rather than a cloud-synced
folder:

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/HeisLazi/python-tutorial-DiddyDungeon.git
cd python-tutorial-DiddyDungeon
git switch feature/cloud-sync-desktop
python3 -m venv .venv
.venv/bin/python -m pip install -r ide/server/requirements.txt
cd ide/frontend
npm ci
cd ../..
git worktree add ../questlab-blackjack feature/quest-lab-ide
chmod +x tools/questlab-launch.sh questlab-state questlab-files
./tools/questlab-launch.sh \
  --workspace ../questlab-blackjack \
  --backend-port 7331 --frontend-port 5173
```

Use `--no-browser` when opening the printed URL manually. The launcher keeps
the backend in stable mode so shell and AI PTYs are not remounted, validates the
branch/upstream identity, and keeps the repository `progress.json` as the one
gateway-owned local cache. Never copy a workspace `progress.json`; use the
state gateway and the explicit `questlab-files` source-transfer flow instead.
The native macOS install and K&M projection run remain an acceptance gate for
the actual Mac machine; this documentation does not claim that gate is passed.

## CachyOS native Linux setup (target; not yet certified)

CachyOS is now an explicit native-Linux target for this branch. The checklist
below is the intended laptop path, but it is not a support claim until the
actual machine completes the acceptance run recorded in F-058.

Use a native Linux filesystem such as `~/projects`; do not run the live app
from `/mnt/c`, OneDrive or a copied Windows `node_modules` tree:

```bash
sudo pacman -S --needed git base-devel python nodejs npm
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/HeisLazi/python-tutorial-DiddyDungeon.git
cd python-tutorial-DiddyDungeon
git switch feature/cloud-sync-desktop
python -m venv .venv
.venv/bin/python -m pip install -r ide/server/requirements.txt
cd ide/frontend
npm ci
cd ../..
git worktree add ../questlab-blackjack feature/quest-lab-ide
PYTHONPATH=. .venv/bin/python -m ide.quest \
  --workspace ../questlab-blackjack \
  --backend-port 7331 --frontend-port 5173 --no-browser
```

Before accepting the install, confirm that `questlab-state runtime`,
`questlab-state authority` and `questlab-state campaign` expose one canonical
state path. Then open the printed Forge URL and run the manual K&M preflight:
trigger one validated local mutation, check live HUD/Journal/Codex/
Character/Homestead projection, and confirm both shell and AI PTYs remain
`CONNECTED` without a refresh. Keep backend reload disabled. Record the
CachyOS kernel/package versions and test evidence in the issue log; if Rollup
or another native optional dependency is missing, rerun `npm ci` inside this
Linux checkout rather than repairing the OneDrive tree. Do not seed Supabase
as part of this local distribution gate.

The native Linux preflight is the PowerShell-free equivalent of the Windows
gate:

```bash
.venv/bin/python tools/questlab-km-preflight.py \
  --backend-port 7331 --frontend-port 5173 --require-isolated-state
```

For a local, cloud-free two-device contract smoke (it uses temporary device
caches and never writes the canonical or legacy save), run:

```bash
.venv/bin/python tools/questlab-local-sync-sim.py --source progress.json
```

This proves revision-aware compare-and-swap conflict detection and an explicit
keep-device resolution through `LocalStateService`; it is not hosted-sync or
two-machine acceptance.

For a repeatable native Linux launch on CachyOS, run the guarded wrapper from
the repository root. It keeps the backend in stable mode so shell and AI PTYs
are not remounted, refuses a stale upstream checkout by default, and passes
the canonical state path through the Python launcher:

```bash
chmod +x tools/questlab-launch.sh
./tools/questlab-launch.sh \
  --workspace ../questlab-blackjack \
  --backend-port 7331 --frontend-port 5173
```

Use `--no-browser` when opening the printed URL yourself. Use
`--allow-stale-checkout` only for an intentional offline session and
`--allow-other-branch` only when reviewing a different branch. Local state
custody is still an explicit review step:

```bash
./tools/questlab-launch.sh \
  --workspace ../questlab-blackjack \
  --migrate-local-state
```

The wrapper never copies a workspace `progress.json`, enables backend reload,
or turns the workspace into a second save authority.

## Choose a quest workspace

The Forge platform checkout owns the canonical local player state. A quest
workspace is only the coding directory for Monaco and the two PTYs. Use a
separate workspace (a sibling worktree is recommended) so health preflight can
prove that the legacy workspace path is distinct from the canonical platform
save:

```bash
git fetch --all
git worktree add ../questlab-blackjack feature/quest-lab-ide
```

Never create or edit a second live save in the workspace. A workspace
`progress.json`, if present, is legacy evidence; use `questlab-state` or the
Forge state service for progression changes.

## Move player-authored source between devices

Campaign progression and project source have separate authorities. To move
the edited `blackjack.py`, Campaign `tutor.py` or `dungeon.py` between your
own PC and laptop, use the explicit WSL helper; do not push the whole
workspace branch because it may contain a legacy save or private notes:

```bash
workspace_root="$(git rev-parse --show-toplevel)"
bash /path/to/python-tutorial-DiddyDungeon/questlab-files \
  --workspace "$workspace_root" --remote-branch 01-blackjack status
```

On the device containing the desired edits, review the status and then run
`push --confirm PUSH_WORKSPACE_FILES`. On the other device, run `pull` for a
hash preview, then `pull --confirm PULL_WORKSPACE_FILES`. A dirty local source
file is not overwritten unless `--allow-overwrite` is also supplied; that
operation makes a temporary backup first. Full commands and the exact
allowlist are in [`WORKSPACE_TRANSFER.md`](./WORKSPACE_TRANSFER.md).

This channel never moves `progress.json`, session notes, secrets, Git history,
or PTYs. It is local/Git-backed for now; signed-in campaign state continues
through the Quest Lab state service/cloud projection.

## Launch from Windows

To prepare a friend-safe source bundle from a reviewed commit, run this from
the clean branch checkout:

```powershell
.\tools\questlab-package.ps1 -OutputDirectory .\questlab-bundles
```

The packager archives committed `HEAD` only, then removes player-owned
`progress.json`, `tutor.py`, `dungeon.py` and `notes/` paths from the staging
tree. It refuses unrelated dirty source changes, so the bundle contains
reviewed source and this guide but never a player save or learning notebook.
It does not install dependencies, so each friend still runs the WSL setup above
inside the extracted checkout.

This is a custody boundary, not a mode removal: Campaign Tutor and Practice
share the same managed `tutor.py` editor/notebook and the workspace-scoped `/api/tutor`
surface. Practice has its own no-reward session/history state and
can save bounded teaching code or concept notes, but it cannot write Campaign
or Dungeon rewards, HP, Resolve, equipment, combat or run state.

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

To opt into per-device local custody after reviewing the preview, add the
explicit switch:

```powershell
.\tools\questlab-launch.ps1 -Workspace ..\questlab-blackjack -MigrateLocalState
```

The launcher prints the source/destination/revision report and asks for
`MIGRATE_LOCAL_STATE` before copying. This applies only to that launch; a
normal later launch stays on the tracked cache until custody is selected
again. It never merges or deletes a workspace/legacy save.

If that local cache is later advanced through the state gateway, an explicit
future `-MigrateLocalState` launch can resume the same cache when the reviewed
source digest and revision are unchanged. The gateway-written custody marker
is the only resume proof; an unmarked cache, changed source, or ambiguous
divergence still stops for review. A normal launch remains on the tracked
cache, and no workspace/legacy `progress.json` becomes authoritative.

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

After reviewing `questlab-state custody`, an approved local-only migration can
be invoked with the reported revision:

```bash
questlab-state custody-migrate --expected-revision 4 --confirm MIGRATE_LOCAL_STATE
```

This copies the canonical snapshot once to the derived per-device cache and
never merges or deletes the workspace/legacy file. Do not run it for a real
save until the source/destination/revision preview has been reviewed; it does
not enable cloud sync or move the default launcher automatically.

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

## Manual K&M preflight

Before accepting a browser checkpoint from a local runtime, run the read-only
gate from the checkout root:

```powershell
pwsh -NoProfile -File .\tools\questlab-km-preflight.ps1 -BackendPort 7331 -FrontendPort 5173
```

It must report `K&M preflight: GREEN`. If it fails on repository identity or
served source markers, do not trust that tab as current-branch UI evidence;
use the runtime's printed ports or restart only through the normal launcher
after preserving any active PTYs. The gate does not write saves, call hosted
state, or restart processes.
