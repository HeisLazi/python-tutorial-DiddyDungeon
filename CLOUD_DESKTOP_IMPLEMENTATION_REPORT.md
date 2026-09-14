# Cloud/Desktop implementation report

Date: 2026-09-15
Branch: `feature/cloud-sync-desktop`

## Milestones

### Milestone A — complete

- Added Vite-safe public Supabase configuration detection.
- Added a dedicated `SyncEngine` boundary and lazy browser client.
- Missing or incomplete cloud configuration keeps Forge in `Offline / Local Mode`.
- Added `ide/frontend/.env.example`; no credentials are committed.
- Initialized the Supabase CLI project configuration without putting a service key in the repository.
- Verified the existing Forge, backend, editor and both PTY routes remain usable.

### Milestone B — implemented and gated

- Added Supabase Auth sign-in, sign-up, sign-out and restored-session handling through `SyncEngine`.
- Added a minimal Settings account surface without scattering Supabase calls through UI components.
- Added account-scoped device registration with a stable per-account UUID and an editable friendly label.
- Local anonymous/offline Forge remains available when cloud configuration is absent or after sign-out.
- The service stores only `{id, user_id, display_name, last_seen_at}` for device writes. It never sends workspace paths, shell history, terminal output, machine metadata or AI credentials.

Hosted Auth is configured to require email confirmation (`mailer_autoconfirm=false`). The automated service tests cover session restoration/sign-in/sign-out with a fake Auth boundary; a real hosted sign-in needs a mailbox the operator controls and was not claimed here.

## Supabase project and schema

- Dedicated project: `Quest Lab` (`ajnxexxcqfbozszwpjpk`) in `HeisLazi's Org`.
- `Lazi-os` was not linked, changed or queried for migrations.
- Migration: `supabase/migrations/20260914000100_profiles_devices.sql`.
- Tables: `public.profiles` and `public.devices`.
- `profiles.id` references `auth.users(id)` with cascade delete; the auth-user trigger creates a profile from display-name metadata or the email local part.
- Device labels are bounded to 80 characters, reject control characters and path-like `/`, `\\` and `:` characters, and are indexed by `user_id`.
- `updated_at` triggers keep profile/device timestamps current.

## RLS policies

Both tables have RLS enabled and anonymous access revoked.

- `profiles_select_own`, `profiles_insert_own`, `profiles_update_own`
- `devices_select_own`, `devices_insert_own`, `devices_update_own`, `devices_delete_own`

Every policy is scoped to `(select auth.uid())`, with matching `WITH CHECK` clauses for writes. `supabase/tests/profiles_devices_rls.sql` runs isolated User A/User B fixtures and proves private reads, cross-user insert rejection and cross-user update protection. The suite passed against the linked Quest Lab database.

## Environment variables

| Variable | Use | Classification |
|---|---|---|
| `VITE_SUPABASE_URL` | Supabase project URL exposed to the browser client | Public |
| `VITE_SUPABASE_ANON_KEY` | Supabase publishable browser key | Public |

The local `ide/frontend/.env.local` is ignored by Git. No service-role/secret key, AI credential, Vercel secret, CLI token or database password is present in tracked files.

## Offline behavior and conflict boundary

Without both public variables, the service does not construct a Supabase client and reports `Offline / Local Mode`; `progress.json`, the local filesystem, Forge, Monaco and PTYs continue to operate. With cloud variables but no session, the Settings surface reports `Sign in to sync`. After sign-out, the local Forge remains usable and the local device-ID map is retained.

This report intentionally stops before Sync Engine v1. No cloud game-state writes or conflict reconciliation are shipped in Milestones A/B. The later C milestone must retain the local cache/outbox and use revision-aware, domain-specific reconciliation; it must never replace a newer cloud state with an older local snapshot.

## Verification commands and results

- `npm test` — 6 cloud configuration/auth/device service tests passed.
- `npm run build` — Vite production build passed.
- WSL Forge launch with no cloud variables — backend health returned HTTP 200; both `/ws/terminal/shell` and `/ws/terminal/ai` executed independent markers.
- WSL `npx --yes supabase db push --linked --yes` — migration applied.
- WSL `npx --yes supabase db query --linked --file supabase/tests/profiles_devices_rls.sql` — `profiles_devices_rls: PASS`.
- WSL `npx --yes supabase db lint --linked` — no schema errors.
- Browser Settings smoke — cloud-configured Forge showed `Sign in to sync`, account creation toggle and device-account surface with no console errors.

## Known limitations / intentionally unimplemented

- Sync Engine v1 player-state migration, offline outbox, conflict UI and two-device reconciliation are deferred to Milestone C.
- Avatar Storage (D), Tauri packaging (E), Vercel surface (F), friends/presence and raid mechanics are not implemented.
- A real hosted sign-in was not claimed because this project requires email confirmation and no operator mailbox was supplied.
- The local FastAPI/PTy backend remains the existing loopback-only process; no Rust rewrite or desktop wrapper was attempted.

## Repair pass — A/B hardening before Milestone C

This repair pass stayed on `feature/cloud-sync-desktop` and used the WSL Forge
runtime for CLI/PTy checks. The Lazi-os project was not linked, edited or
queried. Existing A/B commits were preserved; no reset, rebase or destructive
checkout was used. The scratch `tutor.py` notebook remains intentionally
untracked and player-editable.

### Tutor notebook and terminal lifecycle

- `/api/tutor` now returns a SHA-256 content revision. Forge polls once per
  second while the Tutor view is visible (within the requested 750–1500 ms
  window).
- A clean editor adopts an external write and shows the exact notice
  `PYR updated tutor.py` without a refresh. A dirty editor keeps its text,
  retains the external version, and shows explicit **Reload external version**
  / **Keep my edits** actions plus a visible conflict notice.
- Browser smoke verified both paths against the live WSL Forge: a clean
  external edit updated Monaco; a dirty edit preserved local text and exposed
  the conflict controls; reload then discarded local edits explicitly.
- Terminal lifecycle now keys only on role/banner identity. Font-size and
  terminal-skin changes update xterm options in place, refit and resize the
  existing socket, and do not dispose the PTY. Browser smoke sent a marker,
  changed the font setting, navigated away and back, and observed the marker
  with the shell still `CONNECTED`.

### Security and offline desktop preparation

- Added exact loopback Origin and Host policy. The frontend port comes from
  `QUESTLAB_FRONTEND_PORT`; defaults are only
  `http://127.0.0.1:<port>` and `http://localhost:<port>`. Explicit future
  Tauri origins must be listed in `QUESTLAB_ALLOWED_ORIGINS`; wildcard origins
  are ignored and no Tauri origin is enabled by default.
- Both server entrypoints use `TrustedHostMiddleware`, loopback-only hosts and
  pre-accept WebSocket Origin rejection. WSL tests cover hostile Origin
  rejection, the real Forge Origin, dynamic ports and an untrusted Host.
- Monaco is a direct `monaco-editor` dependency with local Vite worker modules
  (editor/json/css/html/typescript). A production preview loaded the editor
  with `.monaco-editor` present and no console errors or observed external
  resource requirement. The upstream loader's fallback CDN string remains in
  bundled library code but is bypassed by `loader.config({ monaco })`; no CDN
  URL is present in the application source.
- Added root ignore coverage for `.env`, `.env.*`, `!.env.example`,
  `supabase/.temp/`, `node_modules/`, `.venv/`, `__pycache__/`, `dist/` and
  `src-tauri/target/`. A tracked-file credential scan found no credential-like
  values; the only `service_role` match is Supabase's generated role-name
  comment in `supabase/config.toml`.

### State authority, revisions and canon consistency

- Documentation now states the full authority transition: offline/anonymous
  Forge uses local canonical `progress.json`; signed-in Supabase is the
  synchronized account/game-state authority; `progress.json` remains the
  offline cache/device working copy. Progression mutations go through the
  local state/sync service, and GitHub remains source history rather than
  multiplayer transport. `CANON_LEDGER.md` records this as ruleset `1.5.0`
  (`SYS-035`).
- Local canonical mutations use serialized read-modify-write with
  `meta.revision`, UTC `meta.updated_at` and opaque `meta.device_id`. Direct
  editor writes/formatting of `progress.json` are rejected so PYR cannot
  bypass the state boundary.
- `progress.json` now reports rules version `1.5.0` and has no mechanical
  `equipment.weapon` slot. Character, public dashboard and combat-shell
  surfaces present Armor/Trinket/Title; weapon-shaped fantasy remains a
  trinket concept.
- The legacy root dashboard and legacy `ide/server/app.py` remain available
  but are not the active Forge path (`ide/frontend/src/main.jsx` imports
  `AppV2.jsx`; `ide/quest.py` launches `ide.server.app_v2:app`). They received
  the same bounded security/state hardening rather than a broad cleanup.
- Native Windows packaging is documented as a future ConPTY/`pywinpty`
  adapter behind the existing WebSocket contract. Tauri/Rust work is not part
  of this pass.

### Repair verification

- Windows `npm test` — 9 tests passed.
- Windows `npm run build` — passed; 1,343 modules transformed and local
  Monaco worker assets emitted. Vite emitted only the existing large-chunk
  warning (main bundle ~4.8 MB).
- Windows `npm install` reported two package-audit advisories (one low, one
  moderate); no force-upgrade was applied during this bounded repair pass.
- WSL backend:
  `.venv/bin/python -m unittest discover -s ide/server -p "test_*.py" -v`
  — 7 tests passed; `compileall` passed. Python 3.14 emitted only its known
  `pty.forkpty` deprecation warning during the real-Origin test.
- `ruff check` remains non-clean only for the pre-existing BLE001 catches in
  the launcher/legacy server paths; no new repair-specific lint failure was
  introduced.
- Linked Quest Lab Supabase: `db lint --linked` reported no schema errors and
  `profiles_devices_rls.sql` returned `profiles_devices_rls: PASS`.
- WSL live Forge smoke: backend health, independent shell/AI PTY markers,
  real-Origin acceptance and hostile-Origin rejection all passed. Browser
  smoke covered offline Monaco, Tutor clean/dirty sync and terminal-session
  preservation.

### Pre-C local state gateway

The final prerequisite slice adds one bounded local mutation authority before
any player-state Supabase transport begins:

- `POST /api/state/apply` accepts a named command, an explicit `player` or
  `pyr` actor, and an action-specific payload. Unknown actions, fields,
  arbitrary object paths and full snapshots are rejected.
- `python -m ide.state_cli` is a localhost-only bridge. It targets only
  `http://127.0.0.1:<backend-port>/api/state/apply` and exposes bounded
  `learning-event`, `reference-mode`, `homestead-purchase` and
  `homestead-equip` commands. Reward, HP and achievement commands are
  reserved for trusted in-process game code and fail closed in the CLI/HTTP
  surface.
- `player` is limited to player/editor Homestead actions. `pyr` may record
  bounded learning evidence and Reference Mode history, but cannot grant XP or
  coins, manufacture mastery/clean clears, edit Dev Activity or unlock
  achievements. `system` is an internal-only actor for bounded reward, HP and
  achievement handlers.
- The shared service loads the latest local JSON under `PROGRESS_LOCK`,
  validates and mutates only the named action's fields, appends at most 100
  concise `state_events`, bumps `meta.revision`, refreshes UTC
  `meta.updated_at`, preserves a safe existing `meta.device_id`, and writes
  atomically. Homestead routes in both FastAPI entrypoints delegate to it.

Behavioral coverage is now 19 WSL tests plus `compileall`, including bounded
valid/invalid commands, trust denial, arbitrary-path denial, out-of-scope
protection, revision/timestamp/device invariants, concurrent serial revisions,
HTTP behavior, CLI refusal and Homestead delegation. The linked Quest Lab RLS
query also covers a User A `INSERT ... ON CONFLICT ... DO UPDATE` attempt
against User B's device and passes with rejection (`profiles_devices_rls:
PASS`).

### Status and remaining gates

The branch is still intentionally stopped before Milestone C. A real
mailbox-backed signed-in session, two-device cloud game-state save, Sync Engine
v1 outbox/conflict reconciliation, native Windows ConPTY packaging proof and
Milestones D/E/F remain future work. Auth B remains an automated/fake-boundary
verification only: email confirmation is enabled, no operator mailbox was
supplied, and no physical two-device sign-in/restore was claimed. The exact
manual check remains: sign in with a confirmed account on Device A, register
it, sign in with the same account in an isolated Device B profile, restore and
verify the account/device row, sign out, then confirm Forge remains usable
offline with its local device identity. The gateway checkpoint is pushed at
`fa6cb70a12e4ae751a3ef594b6e20e9d69a60162` on
`origin/feature/cloud-sync-desktop`.
