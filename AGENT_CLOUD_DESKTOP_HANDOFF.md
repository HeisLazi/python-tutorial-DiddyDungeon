# Quest Lab Cloud/Desktop Agent Handoff

Target branch: `feature/cloud-sync-desktop`

Base: current Forge v2 / combat foundation from `feature/quest-lab-ide`.

Read before editing:

1. `CANON_LEDGER.md`
2. `TUTOR_CONTRACT.md`
3. `LEARNING_PROTOCOL.md`
4. `GAME_SYSTEM.md`
5. `COMBAT_SYSTEM.md`
6. `FORGE_V2_HANDOFF.md`
7. `CLOUD_DESKTOP_ARCHITECTURE.md`

## Mission

Add cross-device identity/cloud save and prepare Quest Lab to become an installable desktop application without breaking the working local-first Forge experience.

The current working runtime is valuable. Preserve it.

## Hard boundaries

- GitHub remains source-code authority.
- Supabase becomes synchronized account/game-state authority.
- local filesystem remains active coding authority.
- Vercel is a web/public surface, not the privileged PTY backend.
- Before signed-in cloud sync, `progress.json` is local canonical state; after signed-in cloud sync, Supabase is synchronized account/game-state authority and `progress.json` remains the offline/local cache and device working copy.
- do not implement weekly raid combat yet.
- do not redesign the current gameplay or learning protocol.
- do not let the tutor agent write required project files.
- never commit secrets.
- never place a Supabase service-role key in client code.
- never upload AI tokens, shell history, absolute local paths or terminal logs by default.
- keep the local shell/backend loopback-only.
- route progression mutations through the local state/sync service; do not let PYR independently write a cloud-authoritative `progress.json` snapshot.
- use named, trust-scoped state commands through `POST /api/state/apply` (or
  the localhost `python -m ide.state_cli` bridge); never add arbitrary JSON
  patching or direct snapshot writes.
- PTYs intentionally keep the quest workspace as their coding cwd, but the
  launcher must inject the platform package path, backend port and canonical
  state path. Use the `questlab-state` wrapper from a terminal; a workspace
  `progress.json` is legacy evidence and direct edits do not update Forge.
- `.github/workflows/sync-activity.yml` is a separate public-activity
  automation boundary. It is the only workflow that needs `contents: write`,
  uses the ephemeral `GITHUB_TOKEN`, and may publish only the generated
  `activity.json`/`README.md` block to `main`; it must never receive player
  state, PTY, local-code or AI-credential data.

### State-command and Tutor/Practice precision

The public `POST /api/state/apply` envelope accepts only the `player` and
`pyr` trust actors. The `system` actor is reserved for trusted in-process
game code through `apply_internal`; it is rejected by the HTTP route and the
`questlab-state` CLI. Progression rewards, HP and achievement mutations must
therefore remain behind the validated service boundary rather than a caller-
supplied system actor.

Campaign Tutor and Practice intentionally share one managed workspace
`tutor.py` editor/notebook and the dedicated `/api/tutor`/notes routes. They
are separate learning modes because Practice has independent sessions/history
and no Campaign/Dungeon progression writes; Practice is not a second
`tutor.py`, a second notebook, or a normal project-file route.

## Working style

Make bounded, reviewable milestones. After each milestone:

1. run deterministic checks;
2. document what changed;
3. stop and repair failures before moving on;
4. avoid broad opportunistic refactors.

Use `system:` commit-message prefixes for platform/infrastructure commits so Quest Lab Dev Activity does not score maintenance work.

## Milestone A — Cloud configuration foundation

Goal: add configuration structure without requiring cloud availability to launch Forge.

Expected work:
- inspect existing package/runtime structure before choosing exact paths;
- initialize/link Supabase using the installed CLI if the project/account is available;
- add safe `.env.example` documentation with public client values only;
- add a dedicated cloud/sync service boundary rather than direct Supabase calls spread across UI components;
- preserve launch with no Supabase configuration.

Acceptance:
- existing Forge launches with zero cloud env vars;
- missing cloud config produces an offline/local state, not a crash;
- no secrets in Git diff;
- terminal/editor remain working.

## Milestone B — Authentication + profile/device identity

Goal: the same Quest Lab account can sign into multiple devices.

Expected work:
- Supabase Auth;
- `profiles` table;
- device registration with user-chosen/default-friendly display name;
- Row Level Security tied to `auth.uid()`;
- sign in/sign out/session restore surface in Forge or a minimal account surface;
- keep local anonymous/offline mode working.

Acceptance:
- User A cannot read/write User B profile/device rows under RLS tests.
- restarting the app restores a valid signed-in session when appropriate;
- sign-out leaves local Forge usable;
- no local absolute path is stored in the cloud device row.

## Milestone C — Cloud save / Sync Engine v1

Goal: sync core player state between two devices without making Supabase calls from random UI components.

Start with a bounded subset:
- player identity/progression fields;
- HP/max HP;
- equipment armor/trinket/title;
- companion state;
- Homestead ownership/equipped cosmetics.

Do **not** migrate every state domain at once.

Sync requirements:
- local cache remains available;
- offline changes queue locally;
- reconnect attempts sync;
- never blindly replace a newer cloud revision with an older local snapshot;
- log sync status clearly: local / syncing / synced / conflict/error.

Acceptance test with two devices or two isolated local profiles:
1. sign into same account on A and B;
2. change an allowed synced field on A;
3. sync;
4. B receives the newer state;
5. take B offline and make a local allowed change;
6. reconnect;
7. the sync engine reconciles without corrupting the save;
8. Forge works throughout offline mode.

Document the conflict policy used in v1.

### Live RPG projection requirement

Quest Lab progression is not complete if only the underlying save changes. Every player-facing RPG surface must project the latest validated campaign state continuously without a browser refresh and without restarting either PTY.

Use one shared campaign revision/event source for the HUD and game screens rather than independent stale copies.

At minimum, live updates must cover:

- top HUD: level, XP, XP-to-next, lifetime XP where shown, HP, coins, streak, rank, shields and boss count;
- Character: current armor, trinket, title, stats, companion form/bond and newly unlocked gear;
- Homestead: coins, ownership, purchases and equipped cosmetics;
- Quest Journal: current project, active mob, defeated/unlocked mobs, current encounter status, objective completion, enemy Resolve and available Impact objectives;
- Codex: newly encountered/defeated mob records, discovered question/encounter archetypes, concept tags, weaknesses/notes, attempts where recorded, interview history and mastery/shield changes;
- reward/achievement presentation: XP, coins, level-ups, mob clears, next-mob unlocks, gear/trinket unlocks, achievements and mastery/shields.

For combat/encounter state specifically:

- each correctly verified Battle objective/question should apply its predefined Impact and reduce current enemy Resolve immediately;
- an incorrect submitted Battle action may cause the canonical counterattack/HP update after verification;
- the Quest Journal must show the new Resolve/HP state as soon as the state service commits it;
- defeating an encounter must immediately mark the mob defeated, unlock/reveal the next allowed encounter and create/update the related Codex entry;
- Codex knowledge should grow from completed/observed encounters instead of remaining a static preview. Do not reveal hidden exact future answers.

The frontend must not independently invent rewards, Impact, Resolve changes, Codex discoveries or quest progression. It renders validated state-service events/state.

Implementation may use a local subscription/event stream or lightweight revision polling for v1. If polling is used, prefer checking a cheap revision first and only fetching full campaign state when the revision changes. A normal state update must not remount Monaco, Forge PTY or AI PTY.

Acceptance:
1. start with an active mob and visible Resolve;
2. submit/record one valid verified objective;
3. without browser refresh, observe Resolve decrease in Quest Journal;
4. complete the mob;
5. without browser refresh, observe the mob become defeated, the next encounter become available, reward/HUD values update, and a Codex record for the completed mob appear/update;
6. confirm Character/Homestead/Codex/Journal all agree on the same campaign revision;
7. confirm shell and AI terminal sessions remain alive throughout.

## Milestone D — Avatar cloud storage

Goal: replace device-only portrait storage when signed in while retaining a local fallback.

Expected:
- private/user-scoped Supabase Storage bucket/policy;
- validated image type and bounded size;
- profile references avatar asset;
- PC/laptop signed into same account render same avatar;
- offline cached avatar remains visible after prior sync.

Acceptance:
- another user cannot overwrite/read private avatar objects unless deliberately public;
- local fallback still works when unsigned/offline.

## Milestone E — Tauri desktop proof

Only begin after A-D are stable.

Goal: package existing Quest Lab rather than rewrite it.

First Tauri proof must:
- launch as a desktop window;
- display the existing Forge UI;
- start/manage the local privileged backend automatically;
- load a user-selected workspace;
- preserve Monaco editing;
- preserve Forge PTY;
- preserve AI PTY;
- preserve `tutor.py` flow;
- shut child processes down cleanly when the app closes.

Do not implement multiplayer during this milestone.

Prefer retaining the Python/FastAPI backend as a managed sidecar for the first package. Do not rewrite it in Rust unless packaging proves it necessary and document the evidence first.

The current WSL PTY implementation uses POSIX `pty`/`fcntl`/`termios`. For a
future native Windows package, evaluate ConPTY via `pywinpty` behind the same
WebSocket contract and prove clean shutdown; do not start Tauri or a Rust
rewrite in this repair pass.

## Milestone F — Web/Vercel surface

Goal: deploy only the safe web/account layer.

Appropriate web features:
- landing page;
- auth/account entry;
- public profile/character sheet (only explicitly public data);
- desktop download/help page;
- future party/raid lobby placeholder.

Do not expose:
- PTY endpoints;
- local filesystem APIs;
- AI credentials;
- private local code.

## Multiplayer hold point

Stop before implementing real weekly raid mechanics.

At most, after cloud sync + desktop packaging are proven, a later task may add:
- friends;
- presence;
- party create/join;
- a harmless shared realtime counter/state proof.

Do not let this branch jump straight into raid combat/state authority before cross-device save is trustworthy.

## Required final handoff

Update this file or add a concise implementation report containing:
- exact milestones completed;
- files changed;
- Supabase migrations/tables/RLS policies added;
- environment variables required and whether each is public/secret;
- how offline mode behaves;
- conflict policy;
- commands used to test/build;
- known limitations;
- what remains intentionally unimplemented.

Do not claim completion if PC/laptop-equivalent sync and PTY preservation have not actually been demonstrated.

## Current checkpoint — 2026-09-17 — local distribution and Codex hardening

The current published tip on `feature/cloud-sync-desktop` and its `main`
mirror contains the public activity-sync merge and the bounded Codex reader
slice below. The local Forge/Codex work is source-complete for the requested
presentation slice:

- the Codex is a finite, viewport-bounded folio with paged shelves,
  encounters/notes/mastery controls and a separate Battle Shell tab;
- the final reader contract uses a compact header, Books/Battle Shell tabs and
  a bounded two-pane folio so the Codex cannot become an outer infinite feed;
- the shared `.codex-library` primitive no longer carries a legacy feed-sized
  minimum, preventing compatibility-shell cascade regressions;
- the friend packager archives committed `HEAD`, strips player-owned paths,
  and accepts only an exact reviewed `-IgnoreUntrackedPath` for protected local
  directories; it was verified with a 134-entry ZIP and no protected-path leak;
- Campaign Tutor and Practice remain one managed `tutor.py` workspace, while
  Practice progression remains independent and reward-free;
- native Linux/CachyOS launcher and read-only preflight contracts are present;
  actual CachyOS device acceptance is not claimed.

Current verification:

- WSL backend suite: **116/116**;
- Windows frontend suite: **71/71**;
- launcher contract suite: **17/17**;
- Vite production build: **1,346 modules**;
- native Linux launcher/preflight `--help` and shell syntax checks: green;
- fresh disposable ext4 clone: `npm ci`, frontend **69/69**, Vite (**1,346
  modules**) and backend **115/115** passed; the temp checkout was removed;
- native Linux pre-launch report: `tools/questlab-native-report.py --strict`
  now captures kernel/toolchain/checkout/native-Rollup evidence read-only;
- strict clean-ext4 report: **GREEN** with native Rollup, Python `3.14.4`, Node
  `v26.7.0`, npm `11.19.0` and WSL2 kernel `6.18.33.1-microsoft-standard-WSL2`;
- browser K&M attach: still blocked by F-080, so no new visual-device claim.

The latest local presentation checkpoint is F-147: the Codex reader now uses a
single field-guide visual language on top of the bounded folio (quiet paper
surface, compact metric strip, clear shelf spine and readable example blocks).
F-148 also removes the old `min-height: 520px` fallback from the base Codex
primitive. These are CSS-only refinements; they do not add a scroll owner,
change the campaign projection, or remount either PTY.
F-149 removes the remaining base `max-height`/`overflow:auto` fallbacks from
the paged bookshelf and encounter picker. React page controls remain the
authoritative collection navigation, while code examples and long notes keep
their intentional local reading scroll.
F-150 also removes the legacy mobile `max-height: 180px` bookshelf cap so a
compatibility stylesheet order cannot reintroduce a narrow-window scrollbar.
F-151 closes a separate information-leak path: Hub and compatibility Journal
surfaces now render locked chapters/encounters as unknown silhouettes rather
than exposing future names or concepts.
F-152 removes the launch-context heartbeat that masked an unattended 20-minute
gap; `lastSeenAt` now reflects actual interaction rather than elapsed runtime.

F-153 promotes Codex to the full-width surface frame. Its active-quest rail is
still inside the Codex folio, while the shared wide navigation remains the
route switcher. A direct flex rule gives the folio the available height after
navigation instead of letting the Codex inherit an editor-column squeeze or
grow into an outer feed. This is a presentation-only change; no state,
revision, reward, notes, learner-file or PTY contract changed.

F-153 verification: Windows frontend tests **74/74**, Vite (**1,346 modules**)
and `git diff --check` pass. Browser K&M remains blocked by F-080.

Remaining release gates are intentionally unchanged:

1. Apply only the two guarded hosted migrations after explicit approval, then
   run authenticated two-device campaign/avatar/source acceptance.
2. Demonstrate PC/laptop-equivalent live projection and shell/AI PTY survival.
3. Run the clean native CachyOS acceptance and record kernel/package evidence;
   the disposable ext4 build is not a substitute for that physical device.
4. Resolve the browser attach environment before claiming fresh visual K&M.

No hosted migration, seed, player-state write, protected-save migration or PTY
restart was performed in this checkpoint.
