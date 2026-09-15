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
