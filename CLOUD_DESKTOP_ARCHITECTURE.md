# Quest Lab Cloud + Desktop Architecture

**Status:** implementation architecture for `feature/cloud-sync-desktop`.

Quest Lab remains a local-first coding environment. Cloud services add identity, sync, shared game state and future multiplayer; they do not replace the local editor, terminal, filesystem, Python runtime or Git workflow.

## Authority boundaries

### Local filesystem
Authoritative for the active working copy while the user is coding.

Examples:
- project source files;
- `tutor.py`;
- local terminal/PTY sessions;
- Python execution;
- formatter/runtime tools;
- local workspace paths.

### GitHub
Authoritative for project source history and collaboration.

Examples:
- branches;
- commits;
- pull requests;
- shared raid/project source.

GitHub is **not** the live game-state database.

### Supabase
Authoritative for account and synchronized Quest Lab game state.

Examples:
- profiles;
- player progression;
- HP;
- armor and trinkets;
- inventory;
- achievements;
- concept/mastery state;
- Quest Journal/Codex state;
- companion state;
- Homestead ownership/equipment;
- avatar metadata/storage;
- device records;
- later: friends, parties, raid state and realtime raid events.

### Vercel
Hosts the public/web surface.

Examples:
- landing page;
- account/profile pages;
- public character sheet;
- future raid lobby/dashboard;
- download/install information.

Vercel must not host the privileged local terminal backend.

## Local-first principle

Quest Lab must continue working when the internet is unavailable.

Before signed-in cloud sync, `progress.json` is local canonical state. After signed-in cloud sync is enabled, Supabase is synchronized account/game-state authority and `progress.json` remains the local/offline cache and device working copy. Do not delete it during the first cloud-sync milestones. Progression mutations must pass through the local state/sync service so the authority transition is explicit and revision-aware.

Expected flow:

```text
Forge UI
   |
Sync Engine
   |-- local progress cache
   |-- outbound change queue
   |-- Supabase cloud state
   `-- conflict/version metadata
```

The UI should not scatter direct Supabase writes throughout unrelated components. Cloud access should go through a dedicated sync/service layer.

## Data that should sync

- account/profile identity;
- level, XP and coins;
- HP/max HP;
- armor and trinket state;
- inventory;
- projects and quest progress;
- Codex and concept mastery;
- achievements;
- PYR companion state;
- Homestead purchases/equipment;
- discoveries/trophies;
- avatar asset/reference;
- future friends/party/raid state.

## Data that must remain local by default

- AI provider credentials/tokens;
- environment variables/secrets;
- shell history;
- terminal output history unless explicitly submitted;
- absolute local filesystem paths;
- `.venv` / `node_modules`;
- raw private project code outside Git-backed user choices;
- local panel sizes, font sizes and per-device layout preferences.

## Device identity

Each installation may register a device record, for example:

```text
Papasmurff Desktop
TUF Laptop
```

Device identity is for sync/debugging/presence only. It should never expose sensitive hardware or local paths publicly.

## Supabase schema direction

Exact migration names may differ, but keep concerns separated.

Suggested entities:

```text
profiles
player_state
project_progress
concept_mastery
inventory_items
player_inventory
player_equipment
achievements
player_achievements
codex_entries
companion_state
homestead_state
devices
sync_events

later:
friends
parties
party_members
raids
raid_members
raid_objectives
raid_events
```

Prefer row-level security tied to `auth.uid()` from the first migration rather than adding security after data exists.

## Conflict/sync rule

Do not use naive last-write-wins for the entire player document.

At minimum, synced records should carry:
- server-side timestamps;
- version/revision identifiers where useful;
- device/source metadata;
- a small event/outbox queue for offline mutations.

For the first milestone, simple server-authoritative merge rules are acceptable for non-concurrent single-user device sync, but the sync layer must be structured so field/domain-specific conflict handling can be added later.

Never silently overwrite a newer cloud save with an older device snapshot.

The local Forge backend records revision metadata (`revision`, UTC `updated_at`,
and an opaque `device_id`) for canonical local mutations. A later Sync Engine
must compare that metadata before applying cloud changes.

## Desktop direction

Use Tauri as the target desktop shell unless a concrete blocker is discovered.

The first desktop milestone should only prove:

```text
Quest Lab desktop process launches
        |
existing React Forge UI loads
        |
local backend starts automatically
        |
Monaco works
        |
Forge PTY terminal works
        |
AI PTY terminal works
        |
workspace selection works
```

Do not combine the first Tauri milestone with multiplayer implementation.

The existing Python/FastAPI service may initially run as a packaged sidecar or managed local child process. Replacing it with Rust is not a goal unless there is a measured packaging/security reason.

### Native Windows PTY decision for Milestone E

The current WSL/Linux runtime intentionally uses Python `pty`, `fcntl` and
`termios`; those POSIX primitives are not a native Windows desktop contract.
Milestone E must keep the existing WebSocket terminal protocol and choose a
Windows PTY adapter (first candidate: ConPTY through `pywinpty`, with a small
compatibility layer) before packaging. A direct ConPTY proof and shutdown test
are required before calling the desktop milestone complete. This is a packaging
decision for E, not a reason to rewrite the backend in Rust, and no Tauri work
is started in the current repair pass.

## Multiplayer direction

Multiplayer is a later layer on top of a proven cloud-save system.

Supabase Realtime should carry lightweight shared state/events such as:
- party presence;
- raid membership;
- objective status;
- verified Impact events;
- Resolve changes;
- downed/revive events;
- raid completion.

The shared software project itself remains Git-backed.

For a future weekly raid:

```text
GitHub = shared project/source truth
Supabase = raid/game state truth
Local Forge = active coding environment
PYR = controlled verifier/tutor
```

## Security boundaries

Never ship:
- Supabase service-role keys in the client;
- Vercel secrets in frontend code;
- AI provider API keys/tokens to Supabase;
- raw shell command history to the cloud by default;
- unrestricted remote shell access;
- a publicly reachable FastAPI/PTTY backend.

The local privileged backend continues to bind only to loopback unless a future authenticated transport is explicitly designed.

The backend accepts only exact `http://127.0.0.1:<frontend-port>` and
`http://localhost:<frontend-port>` browser origins, where the port comes from
`QUESTLAB_FRONTEND_PORT`. A future Tauri webview origin (such as
`tauri://localhost` or `http://tauri.localhost`) must be explicitly added to
`QUESTLAB_ALLOWED_ORIGINS` only after packaging verifies the origin; no wildcard
origin is permitted or enabled by default. Host validation remains restricted
to `127.0.0.1` and `localhost`.

## Migration order

1. Supabase project linking/config and environment templates.
2. Auth + `profiles` + device registration.
3. Sync engine abstraction and cloud-save transport.
4. Migrate current `progress.json` domains incrementally while retaining local cache/offline operation.
5. Avatar storage/profile sync.
6. Cross-device sign-in and verified PC/laptop sync.
7. Tauri shell around the stable local Forge runtime.
8. Installer/build flow.
9. Friends/presence/party primitives.
10. Raid shared-state proof-of-concept.
11. Only then implement live weekly boss mechanics.

## Non-goals for the first implementation pass

- rewriting gameplay;
- replacing Forge v2 UI;
- changing tutoring rules;
- changing XP/combat balance;
- building weekly raids;
- building a custom Git hosting layer;
- replacing GitHub with Supabase;
- removing offline/local operation;
- rewriting the Python backend in Rust.
