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

Hosted Auth is configured to require email confirmation (`mailer_autoconfirm=false`). The automated service tests cover session restoration/sign-in/sign-out with a fake Auth boundary; a hosted mailbox sign-in remains an operator-owned acceptance check and is not claimed solely from source tests.

### Milestone C — bounded Sync Engine v1 implemented and gated

- Added the allowlisted local projection endpoints `GET /api/state/sync` and
  `POST /api/state/sync/apply`. Cloud pulls therefore enter the same locked
  state service as PYR/player mutations and cannot write a second
  `progress.json` authority.
- Added `supabase/migrations/20260915000100_player_state.sql` plus the
  corrective `supabase/migrations/20260915000200_player_state_rpc_validation_fix.sql`,
  bounded-value `supabase/migrations/20260915000300_player_state_value_bounds.sql`,
  and the executable `supabase/tests/player_state_rls.sql`.
  `public.player_state` is
  one RLS-protected row per account; authenticated clients can select only
  their own row and can write only through the
  `save_player_state(expected_revision, next_state, source_device_id)`
  compare-and-swap RPC. Direct table writes are revoked.
- `SyncEngine` now owns all player-state Supabase reads/writes. The bounded
  projection syncs player progression/HP, armor/trinket/title, companion
  state, Homestead ownership/equipped cosmetics, and the validated campaign
  evidence needed to keep project/mob progress, Codex, goals/skills and a
  Dungeon checkpoint coherent. Event logs, activity, profile data and
  cosmetic catalog/purchase history remain local and are preserved by cloud
  pulls.
- A per-account cursor and bounded eight-entry local outbox survive offline
  operation. Reconnect pushes only a revision captured from the local gateway;
  if the cloud revision moved, the engine fails closed with `conflict`.
  Missing/decreasing revisions and same-revision projection drift also require
  an explicit choice. Settings exposes non-blocking **Use cloud copy** and
  **Keep this device** actions; neither side is selected by timestamp or
  newest-file heuristics.
- Account status now reports `local`, `syncing`, `synced`, `conflict` or
  `error`, including queued-change count. Local Forge remains usable while a
  cloud request is unavailable, and the existing browser campaign revision
  polling/reward queue continues to drive every RPG surface without a refresh
  or PTY remount.
- A signed-in browser performs a lightweight two-second cloud-row check with
  in-flight deduplication, so another device's accepted projection is pulled
  into the same local revision/event stream automatically.
- First-device bootstrap is now automatic when the cloud row is still the
  untouched starter projection and the local cache contains validated progress:
  the local projection is published through the compare-and-swap RPC, the
  cloud revision increments, and the normal live campaign polling picks it up
  on other signed-in devices. A non-starter cloud projection still raises an
  explicit conflict; no timestamp or newest-file heuristic is used.

### Milestone D — Avatar cloud storage implemented and gated

- Added the private `avatars` bucket and account-scoped Storage RLS policies.
  Each account has one fixed object path, `<auth-user-id>/avatar.webp`; the
  profile stores only that bounded reference in `avatar_path`.
- Avatar uploads accept PNG/JPEG/WebP source files up to 5 MB, center-crop to a
  256px WebP and enforce a 1 MB cloud payload limit before calling Supabase
  Storage. The bucket independently enforces the WebP type and 1 MB limit.
- `SyncEngine` owns avatar upload, profile-reference update, download and
  removal. Forge controls call that boundary when signed in and retain the
  existing local-only path when offline or anonymous.
- Successful downloads are cached under an account-scoped local key and
  delivered through `questlab:avatar-updated`; a previously synced portrait is
  restored from that cache during an offline session without blocking gameplay.
  Async avatar work is invalidated when the account changes or a newer upload /
  removal starts, so a stale download cannot resurrect a removed portrait.

### Forge roadmap — bounded PYR context bridge implemented

- Added read-only `GET/POST /api/pyr/context` endpoints. The bridge combines
  the current canonical campaign revision/encounter projection with an
  explicitly captured active file, Monaco selection and Forge terminal tail.
- Context includes only the current quest/mob/concept and assistance/Clean
  Clear state; future locked encounter prompts/answers are not projected.
  Active file and terminal/diff text are UTF-8/ANSI cleaned and byte-bounded.
- Git context excludes `progress.json` and secret-looking files. The bridge
  stores only the latest ephemeral editor/terminal capture in memory and never
  writes player state or bypasses the state service.
- Submit Run now asks the bridge for a structured context payload before
  sending it to the selected local AI terminal. If the bridge is unavailable,
  the existing safe fallback remains available.
- Added a challenged `POST /api/pyr/verdict` boundary for the next combat
  slice. A one-time nonce binds a correct/incorrect verdict to the captured
  campaign revision and active mob; only canonical objective Impact, rewards,
  armor and counterattack values can be applied by the state service.
- A verdict for an available objective now records the encounter attempt in
  the canonical encounter projection and Codex. Correct outcomes add verified
  evidence; incorrect outcomes retain the question type, result and bounded
  note without granting mastery evidence. The route returns these validated
  mutation/event details for the existing live projection and reward queue.
- The Quest Journal now provides an optional Battle answer form. A submission
  is bound to the current objective and an answer digest in memory, then sent
  to the selected local AI terminal with exact verdict tokens. The canonical
  state service remains the only writer; the form cannot award Impact, XP,
  coins, HP or rewards. Provider authentication is still required before a
  hosted Battle release.
- Added the first Infinite Dungeon save-state slice. `dungeon_run` is stored
  under the canonical state service, starts with Apprentice Coat/no trinket/one
  heal, and exposes a controlled `dungeon.py` projection. A saved editor buffer
  and floor/room/question survive a Forge or workstation restart; question
  rotation and recorded death clear the buffer. Direct `/api/file` access to
  the projection is rejected so it cannot become a second save authority.
- Added separate Dungeon and Practice surfaces. Dungeon is run-scoped and
  restart-safe; Practice lets the player choose a concept, question type and
  difficulty for unlimited provider-assisted drills above the same managed
  `tutor.py` editor/notebook and bounded notes channel. Practice cannot mutate
  Campaign/Dungeon rewards, HP, Resolve, equipment, combat or run state.
  Adaptive generation, rooms, markets, scoring and hosted leaderboards remain
  later slices.
- Restored Tutor Notebook as a first-class shared Tutor/Practice surface. Its
  dedicated `/api/tutor` endpoint and editor support collaborative teaching
  examples; generic project-file routes still reject `tutor.py`, while the
  dedicated Tutor/notes routes remain the only bounded learning-workspace
  writes.

## Supabase project and schema

- Dedicated project: `Quest Lab` (`ajnxexxcqfbozszwpjpk`) in `HeisLazi's Org`.
- `Lazi-os` was not linked, changed or queried for migrations.
- Migrations: `supabase/migrations/20260914000100_profiles_devices.sql` and
  `supabase/migrations/20260915000400_avatar_storage.sql`.
- Tables: `public.profiles` and `public.devices`; `profiles.avatar_path` is a
  bounded account-owned reference to the private `avatars` Storage bucket.
- `profiles.id` references `auth.users(id)` with cascade delete; the auth-user trigger creates a profile from display-name metadata or the email local part.
- Device labels are bounded to 80 characters, reject control characters and path-like `/`, `\\` and `:` characters, and are indexed by `user_id`.
- `updated_at` triggers keep profile/device timestamps current.

## RLS policies

Identity tables have RLS enabled and anonymous access revoked. The private
`avatars` bucket has owner-only object policies for select/insert/update/delete
and accepts only the fixed `<auth-user-id>/avatar.webp` path.

- `profiles_select_own`, `profiles_insert_own`, `profiles_update_own`
- `devices_select_own`, `devices_insert_own`, `devices_update_own`, `devices_delete_own`
- `avatars_objects_select_own`, `avatars_objects_insert_own`,
  `avatars_objects_update_own`, `avatars_objects_delete_own`

Every policy is scoped to `(select auth.uid())`, with matching `WITH CHECK` clauses for writes. `supabase/tests/profiles_devices_rls.sql` runs isolated User A/User B fixtures and proves private reads, cross-user insert rejection and cross-user update protection. The suite passed against the linked Quest Lab database.

## Environment variables

| Variable | Use | Classification |
|---|---|---|
| `VITE_SUPABASE_URL` | Supabase project URL exposed to the browser client | Public |
| `VITE_SUPABASE_ANON_KEY` | Supabase publishable browser key | Public |

The local `ide/frontend/.env.local` is ignored by Git. No service-role/secret key, AI credential, Vercel secret, CLI token or database password is present in tracked files.

## Offline behavior and conflict boundary

Without both public variables, the service does not construct a Supabase client and reports `Offline / Local Mode`; `progress.json`, the local filesystem, Forge, Monaco and PTYs continue to operate. With cloud variables but no session, the Settings surface reports `Sign in to sync`. After sign-out, the local Forge remains usable and the local device-ID map is retained.

The bounded C/D slices are now implemented, but hosted acceptance remains
gated until a confirmed-mailbox account can exercise two-device state and
avatar transport. The local cache/outbox is authoritative while offline, and a
newer cloud revision is never replaced by an older device snapshot.

## Verification commands and results

- `npm test` — 21 frontend cloud/runtime/sync/context tests passed.
- `npm run build` — Vite production build passed.
- WSL Forge launch with no cloud variables — backend health returned HTTP 200; both `/ws/terminal/shell` and `/ws/terminal/ai` executed independent markers.
- WSL `npx --yes supabase db push --linked --yes` — profiles/devices, all three
  player-state migrations and the private avatar bucket migration applied.
- WSL `npx --yes supabase db query --linked --file supabase/tests/profiles_devices_rls.sql` — `profiles_devices_rls: PASS`.
- WSL `npx --yes supabase db query --linked --file supabase/tests/player_state_rls.sql` — `player_state_rls: PASS`.
- WSL `npx --yes supabase db query --linked --file supabase/tests/avatar_storage_rls.sql` — `avatar_storage_rls: PASS`.
- WSL `npx --yes supabase db lint --linked` — no schema errors.
- WSL `.venv/bin/python -m unittest discover -s ide/server -p "test_*.py"` —
  34 backend tests passed, including bounded context/state-file isolation.
- Browser Settings smoke — cloud-configured Forge showed `Sign in to sync`, account creation toggle and device-account surface with no console errors.

## Known limitations / intentionally unimplemented

- An independently verified hosted PC/laptop player-state run is still
  pending; the bounded Sync Engine v1 migration, outbox, conflict UI and
  isolated two-engine reconciliation are implemented and tested.
- Hosted avatar upload/download acceptance, Tauri packaging (E), Vercel surface
  (F), friends/presence and raid mechanics remain future work.
- A provider-authenticated browser-level PYR verdict path is still pending. The
  local context/submission/verdict boundary and Journal form are implemented,
  but the raw local AI terminal remains a trusted caller; do not treat an
  unauthenticated caller-supplied verdict as proof of learning.
- Infinite Dungeon's local checkpoint/projection slice now includes question
  generation, state-service verdict progression, room rotation, rest/market
  rooms, death/reset handling, score/currency and local leaderboard persistence;
  the K&M acceptance is recorded below. Hosted/provider persistence remains
  gated by F-018.
- Practice now records bounded sessions, provider-reviewed results and local
  history through the state service; provider authentication and hosted
  persistence remain future gates rather than local implementation gaps.
- The durable review findings for the context/verdict/Battle slices are tracked
  in `FORGE_ROADMAP_ISSUES_LOG.md`; open trust and concurrency gates remain
  listed there.
- A real hosted sign-in was not independently verified in this run; this
  project requires email confirmation. A signed-in account still needs the
  hosted two-device acceptance below.
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

- Windows `npm test` — 17 tests passed.
- Windows `npm run build` — passed; 1,343 modules transformed and local
  Monaco worker assets emitted. Vite emitted only the existing large-chunk
  warning (main bundle ~4.8 MB).
- Windows `npm install` reported two package-audit advisories (one low, one
  moderate); no force-upgrade was applied during this bounded repair pass.
- WSL backend:
  `.venv/bin/python -m unittest discover -s ide/server -p "test_*.py" -v`
  — 29 tests passed; `compileall` passed. Python 3.14 emitted only its known
  `pty.forkpty` deprecation warning during the real-Origin test.
- `ruff check` remains non-clean only for the pre-existing BLE001 catches in
  the launcher/legacy server paths; no new repair-specific lint failure was
  introduced.
- Linked Quest Lab Supabase: `db lint --linked` reported no schema errors and
  `profiles_devices_rls.sql` returned `profiles_devices_rls: PASS`.
- The linked Quest Lab project accepted both player-state migrations;
  `db lint --linked` reported no schema errors and
  `db query --linked --file supabase/tests/player_state_rls.sql` returned
  `player_state_rls: PASS`. The initial push exposed an unavailable
  `jsonb_object_length` function; the corrective migration replaced it with
  compatible JSON-key-loop validation before the final clean lint/test run.
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

Behavioral coverage is now 25 WSL tests plus `compileall`, including bounded
valid/invalid commands, trust denial, arbitrary-path denial, out-of-scope
protection, revision/timestamp/device invariants, concurrent serial revisions,
HTTP behavior, CLI refusal and Homestead delegation. The linked Quest Lab RLS
query also covers a User A `INSERT ... ON CONFLICT ... DO UPDATE` attempt
against User B's device and passes with rejection (`profiles_devices_rls:
PASS`).

### Split-brain state repair and live RPG projection

The learning-session bug was a real two-file authority split. Before changing
state, the candidate files were inspected read-only:

- The WSL platform checkout `/home/lazi/projects/python-tutorial-DiddyDungeon/progress.json`
  was schema 4/rules 1.3 at Level 1, 0 XP, 0 coins and 0 defeated mobs.
- The WSL quest workspace `/home/lazi/projects/questlab-blackjack/progress.json`
  was an older schema 2 save at Level 2, 50 XP (150 lifetime XP), 55 coins,
  three defeated mobs and 38% project progress. Its session log recorded the
  first three Blackjack mobs as cleared.
- Before reconciliation, the active Windows checkout canonical file
  `C:\Users\lazar\OneDrive\Documents\ChatGPT\Python Quest Lab\progress.json`
  was schema 4/rules 1.5 with revision 0 at Level 1, 0 XP and 0 coins. It was
  later reconciled through the same internal state-service action; it is now
  revision 2 at Level 2 with the validated Blackjack projection described
  below.

The workspace copy is therefore treated as legacy evidence, never as a second
live save. No timestamp or “newest file wins” merge was performed. The bounded
`/api/state/legacy` report and `python -m ide.state_cli legacy-report` expose
summaries and field-level differences, mark manual approval as required, and
do not copy or infer rewards. `/api/file` and `/api/format` reject both the
canonical and stray workspace `progress.json` paths. The launcher explicitly
sets `QUESTLAB_STATE_PATH` to `REPO_ROOT/progress.json`; relative overrides are
anchored to `REPO_ROOT`, so a PYR/CLI terminal cwd cannot create another active
player save.

The Forge now exposes a cheap `/api/state/revision` endpoint and returns the
validated encounter projection with each campaign snapshot. React and the
combat shell poll the revision about once per second and reload the full
campaign only after a change. State-service events are the sole source for the
reward queue (objective Impact/Resolve, XP, coins, level-up, mob defeat, next
encounter, achievements, equipment and mastery fields); React does not
recalculate rewards or reveal locked future questions. The Quest Journal shows
only the current encounter's allowed objective metadata, while the Codex grows
only from recorded encounter evidence.

Live acceptance used a disposable copy of the canonical save and an actual
WSL-launched FastAPI/Vite Forge page, without refreshing the browser or
resetting either PTY:

1. Initial projection was revision 0, Level 1, 0/100 XP, 0 coins, The Empty
   Table and Resolve 4/4.
2. A trusted in-process `record_battle_objective(table_setup)` mutation moved
   revision 1 to Resolve 2/4; the HUD and battle shell stayed in place.
3. `record_battle_objective(state_explanation)` moved revision 2 to 25 XP,
   10 coins, defeated The Empty Table, unlocked The Dealer's Hand (Resolve
   6/6), and added the defeated encounter to the Codex. Character showed
   25/100 XP and 10 coins; Homestead showed a 10-coin purse. The reward queue
   displayed validated next-encounter and First Blood notices.
4. A third verified objective moved the live next encounter to Resolve 3/6;
   the queue displayed `OBJECTIVE VERIFIED` with the service-provided 3 Impact.
   A bounded reward test then moved revision 4 to Level 2 and 5/100 XP; the
   queue displayed `LEVEL UP 1 → 2`.
5. Both shell and AI terminal connection pills remained `connected` throughout,
   and seeded PTY markers remained present after every projection update.

The live HUD icon regression was also fixed. The stat-pill rule now targets
only direct `.top-stats > span` children; nested `.quest-icon` SVG wrappers and
`data-stat-value` spans explicitly keep transparent backgrounds, zero pill
padding/borders and the existing monochrome stroke sizing. Adventurer and
compact selectors use the same direct-child boundary, and the batched DOM
enhancement observers leave the icons intact across revision polling.

The follow-up HUD jump was traced to the background SyncEngine poll setting the
top cloud pill to `Syncing…` and then `Synced` on every unchanged two-second
check. Background polls now use a silent path that preserves a settled status;
explicit mutations, reconnects, conflicts and errors still surface normally.
The cloud pill also reserves a fixed width with ellipsis so status text cannot
push the HP/coins/streak/shield/boss stat pills around. A regression test keeps
the silent poll from emitting a transient `syncing` state.

The stray-save proof edited only the disposable workspace copy to Level 99,
9999 coins and revision 999. The canonical API still reported revision 4,
Level 2 and 10 coins, with `legacy_authoritative: false`; the stray file could
not create a second game state.

### Approved legacy Blackjack reconciliation

The operator explicitly approved a bounded reconciliation after the live
learning session. I read the legacy `legacy-report` endpoint (also through
`python -m ide.state_cli legacy-report`), the legacy `progress.json`,
`SESSION_NOTES.md` and `HANDOFF.md` before selecting fields. The real legacy
file was never edited. Its SHA-256 was
`200f5b8c1c87040dc522dbf6f8397c47c035bd036312601ee731180021e6744c` both
before and after the operation, and the report continues to mark
`legacy_authoritative: false` and `manual_approval_required: true`.

The approved payload was sent to the internal `system` action
`reconcile_legacy_progress` on the canonical state service. It was an
allowlisted, read/modify/write mutation rather than a snapshot copy. The
canonical WSL path is `/home/lazi/projects/python-tutorial-DiddyDungeon/progress.json`;
the post-reconciliation file SHA-256 is
`3d67a950fa9c57bf2e7b0bdd738b56ec82490fbebc7ecb937c2889a848817116` and its
state revision is `2`. Two audited `state_events` were created (the second
added only the additionally reviewed current-goal mappings), both carry
`reconciliation: approved_legacy_evidence` and
`reward_history_inferred: false`. The action is internal-only over HTTP/CLI,
so an ordinary PYR command cannot manufacture a migration or write a second
save.

The same allowlisted payload was then applied on the laptop checkout through
its local state gateway. The Windows canonical cache
`C:\Users\lazar\OneDrive\Documents\ChatGPT\Python Quest Lab\progress.json`
finished at revision `2` with SHA-256
`b80c89ce3606f626f5b0565ad121f03fb14868d92410933d338f3fbc03ce607`.
The legacy workspace hash remained
`200f5b8c1c87040dc522dbf6f8397c47c035bd036312601ee731180021e6744c`; it was
read-only evidence and was not edited.

Restored because the report and session evidence agree:

- Player Level 2, 50/100 current XP, 150 lifetime XP and 55 coins.
- Session/explanation counters of 1 and 3, respectively; three defeated mobs.
- Current streak 1, longest streak 1, and the logged date `2026-09-14`.
- Blackjack project progress 38%; `The Empty Table`, `The Dealer's Hand` and
  `The Count Keeper` are defeated; only `The Hitman` is unlocked next.
- The active `The Hitman` encounter is in Forge phase with canonical Resolve
  8/8 and only its allowed `CODE_CHECKPOINT` (4 Impact) and `BUG_DIAGNOSIS`
  (4 Impact) objective metadata exposed. No partial Resolve reduction was
  inferred because the legacy evidence contained none.
- The validated `First Blood` achievement.
- Current daily equivalents `learn-before-forge`, `first-deal` and
  `explain-lists`; weekly progress `three-sessions: 1/3` and
  `two-mobs: 2/2`. The separate first-interview goal remains 0/1.
- The reviewed current quest/last-session text, Forge learning phase and the
  canonical Mob 3 concept.
- Three Codex encounter records for the defeated mobs, each tagged with its
  canonical concept, defeated status and the evidence id. They contain no
  fabricated attempts, question types, weaknesses, interview history or
  mastery shield; each record carries an explicit note that those facts and
  exact rewards were not inferred.

Not restored because it was absent or contradictory in structured evidence:

- No equipment or upgrade beyond the existing starter loadout (Apprentice
  Coat, no trinket, Apprentice Coder title) was claimed.
- Companion remains PYR, Tiny Code-Flame, level 1, bond 0. No companion reward
  evidence was present.
- The legacy file reports zero interview passes and zero shields. A prose note
  mentions a Functions/Lists interview, but without a structured result it was
  not enough to grant mastery, a shield or a first-interview completion.
- Exact legacy reward history, individual question attempts, weaknesses,
  discoveries/bonuses, boss clears and later quest unlocks were not replayed.
  Aggregate XP/coin totals were restored as reviewed facts only; no per-reward
  history was invented.

Live Forge acceptance used the current branch source with the canonical WSL
state service at `http://127.0.0.1:7333` and the Forge tab at
`http://127.0.0.1:5174/`. While that tab was open, the second audited
reconciliation committed revision 2. No browser refresh occurred: the
one-second revision poll delivered the first event's `PROGRESS RESTORED`,
`NEXT ENCOUNTER` and `CODEX UPDATED` feedback, then accepted the second
revision's goal-only update; the renderer now gates each notification on the
event's changed-field list. The same tab then showed:

1. HUD/Character values Level 2, 50 XP and 55 coins (plus the existing HP,
   streak and starter loadout).
2. Quest Journal progress 38%, the three defeated mobs, Mob 3 `The Hitman`,
   and Resolve 8/8 with the two allowed objectives.
3. Codex entries for all three fought mobs with their concepts and evidence
   notes.
4. Homestead purse 55 and the unchanged starter cosmetic ownership.
5. Shell and AI terminal pills `CONNECTED`; the current backend PTY children
   remained 73138 and 73163. The pre-existing user Forge PTYs (41367 shell,
   41376 AI with agy 41422) were not reset or modified.

The direct stray-file check remains negative: changing a temporary legacy path
in the isolated state-service tests never changed the canonical revision, and
the real legacy file hash above is unchanged. There is one active local state
authority exposed by the service; the workspace `progress.json` is evidence
only.

### Sync Engine v1 verification

The frontend sync harness uses two isolated engine instances sharing one fake
account row and separate local caches. It proves initial local push, cloud pull
to the second cache, an offline local mutation retained in the per-account
outbox, reconnect push at the expected cloud revision, and a concurrent cloud
change that surfaces an explicit conflict. Selecting the cloud copy applies it
through `/api/state/sync/apply`; no direct `progress.json` or React reward
mutation is used. The source tripwire also checks that `AppV2` observes every
campaign revision and that Settings exposes both conflict choices.

### Status and remaining gates

The bounded Milestone C slice and the Milestone D avatar boundary are
implemented and gated. A real mailbox-backed signed-in session, hosted
two-device player-state save, and hosted avatar upload/download still need to
be demonstrated; the automated harness is not a claim of that physical
acceptance. Native Windows ConPTY packaging proof and Milestones E/F remain
future work, as do friends/presence and raid mechanics. A confirmed session
still needs the hosted Device A/Device B acceptance: sign in with the same
account, verify the allowed projection and portrait arrive, keep both PTYs
alive, then exercise an explicit conflict choice. The final remote branch SHA
is recorded after the verification commit.

### Signed-in laptop state clarification

The first signed-in device with a validated local campaign now bootstraps an
account that still has the untouched starter cloud row. The SyncEngine publishes
that projection through `save_player_state`, records the new cloud revision and
shows a short “published to the starter cloud copy” detail. This removes the
Level 2/local versus Level 1/cloud split without requiring a manual choice.
**Keep this device** remains available for a true non-starter conflict, where
both devices contain independent progress and neither copy may silently win.
The portrait shown in the rail/Character is likewise a browser-local
`localStorage` avatar; account-wide avatar sync is reserved for Milestone D, so
its persistence after refresh does not prove that player state has synced.

### Follow-up stale projection repair

A compatibility gap remained in the DOM combat enhancement: older approved
legacy projections use mob status `cleared`, while the current state service
uses `defeated`. When no `available` entry was present, the enhancement could
therefore select an already-cleared mob (for example, The Empty Table) as the
current encounter. `combatShell.js` now treats both statuses as terminal, and
the Quest Journal/context list uses the same rule. The regression is covered by
the frontend source test `combat projection treats legacy cleared mobs as
terminal`.

Cloud conflicts now also include a bounded Level/XP/coins summary for the local
and cloud projections in Settings. This keeps real conflicts visible as a
deliberate sync choice instead of looking like a silent local reset. Homestead
purchases continue to use the canonical `/api/homestead/purchase` mutation and
refresh the campaign projection after the validated result.

### Dungeon projection hardening — 2026-09-15

The local Infinite Dungeon foundation received a focused correctness pass before
Milestone C. Checkpoint writes now include the current question ID and reject a
late save from a rotated question, while debounced autosave keeps the editor
responsive and never discards newer local input. Campaign revision polling also
materializes the canonical `dungeon.py` projection and degrades to a safe
invalid/empty Dungeon projection if a legacy or malformed file is encountered;
the campaign HUD remains available. Direct generic file access to legacy
`tutor.py` is blocked, and both terminal bridges ignore unknown JSON control
envelopes and reap PTY children before closing descriptors; the live browser
check exercised that PTY lifecycle without dropping either session.

The browser acceptance was run with keyboard/mouse automation only (no
Playwright) against a disposable isolated state copy. It verified live reward
feedback, Resolve and Codex changes, Character/Homestead projection updates,
the monochrome SVG HUD icons, checkpoint restoration after a backend restart,
and `CONNECTED` shell/AI PTYs. WSL backend tests: 39 passed; frontend tests: 24
passed; Windows Vite build: passed. No real `progress.json`, legacy evidence,
user PTY or Supabase state was modified.

### Runtime checkout visibility note — 2026-09-15

The screenshot came from the already-running Forge on port 5173. Its process
command line points at `/home/lazi/projects/python-tutorial-DiddyDungeon` on
`feature/quest-lab-ide`, not this `feature/cloud-sync-desktop` checkout. That
runtime therefore served an older AppV2/CSS bundle (including the broad
`.top-stats span` rule) and could not show the newer Dungeon/Practice/sync
surfaces. I applied only the frontend selector/icon-persistence repair to that
running checkout; its backend, canonical save and connected shell/AI PTYs were
left alone. A fresh port-5174 tab served this branch and showed the expected
monochrome SVG stat icons and Campaign Tutor destination. The launcher still
needs to target this checkout before the new branch features will be visible at
the user's usual port.

### Roadmap execution baseline and authority routing — 2026-09-15

`GAME_STATE_SNAPSHOT_2026-09-15.md` and `ROADMAP_EXECUTION_PLAN.md` are the
persistent baseline and dependency-ordered delivery plan for the remaining
Campaign, Codex, Homestead, Dungeon, Practice, distribution and friend
features. The plan was approved with these defaults: boss XP requires separate
behaviour/explanation/interview evidence; Dungeon is local-first; sharing is
opt-in and excludes code/private notes; AI custom encounters must be grounded
in recorded weakness evidence; Campaign Tutor and Practice remain separate;
the current PTYs are not reset.

The first completion slice is now implemented in the worktree. A final mob
clear sets `mob_sequence_complete` and `boss_status=available`, increments only
the canonical mob reward, and emits a `BOSS GATE UNLOCKED` event. Trusted game
code may then call the internal `record_boss_clear` action with bounded
behaviour, explanation and interview evidence IDs. The service derives the
documented +100 XP boss reward, project/boss counters, Housebreaker/Clean Clear
when justified, the first-boss long-term goal and Tiny Code-Flame → Ember
Sprite evolution. A mob clear never silently counts as a boss victory.

The PTY routing fix is also in the worktree. Both terminal bridges now inject
the repo package path, backend port, canonical state path and explicit legacy
path diagnostics. The `questlab-state` wrapper and read-only `authority`/
`campaign` CLI commands work from the quest workspace. Raw workspace
`progress.json` edits remain intentionally non-authoritative: they cannot bump
the canonical revision, create state events, update the HUD, or enter cloud
sync. PYR must use named state-service commands.

Focused verification for this slice: 38 WSL backend tests and 26 frontend
source tests pass. The full WSL discovery run currently reports 43 tests with a
flaky PTY-origin test cancellation under Python 3.14; it is being isolated and
must be green before this checkpoint is committed. Windows Vite/K&M gates are
still pending for the new slice. Claude Sonnet review remains unavailable from
WSL until its CLI is authenticated; no external approval is claimed.

### Current local roadmap checkpoint — 2026-09-15

The local playable roadmap slices are now complete through Campaign, Codex,
Homestead, Infinite Dungeon and Practice. The Campaign Tutor Notebook remains
its own first-class surface; Practice is a separate unlimited mode and never
writes `tutor.py` or grants Campaign/Dungeon state.

Infinite Dungeon now has a canonical, provider-routed unauthenticated
answer/verdict bridge,
adaptive focus based only on recorded Codex incorrect-result/weakness evidence,
progressive encounter/rest/market rooms, run-only score/coins, death reset,
checkpoint persistence, blank editor rotation and a bounded local leaderboard.
Practice has bounded sessions, mixed question types and provider-validated
attempt history with no reward/HP/Resolve/Campaign mutation. The Codex is a
searchable concept-page projection with validated encounter observations and a
bounded player-note action. All visible rewards and progression remain event
results from the state service.

The fresh K&M acceptance used only click/scroll/type automation (no
Playwright) against an isolated current-branch runtime at port 5181. It showed
Level 2 / 50 XP / 55 coins, the repaired monochrome SVG HUD icons, three
cleared Blackjack mobs, The Hitman at 8/8 Resolve, 38% progress, Character and
Codex projections, Dungeon checkpoint/leaderboard behavior, and the Practice
boundary. A typed external state-gateway Dungeon start appeared in the view
after revision polling without a refresh. Shell and AI PTY labels stayed
`CONNECTED`; the real canonical save, legacy files and existing user PTYs were
not touched.

For the specific gold-sync regression, a typed compare-and-swap state-service
projection changed only the disposable cache's coins from 55 to 54. The HUD
changed to 54 after the next revision poll without a refresh, proving the same
revision source drives the header as well as Dungeon/Character/Homestead views.

Latest automated gates are 47 WSL backend tests, 29 frontend tests and a green
Windows Vite production build. WSL Vite remains blocked only by the shared
Windows `node_modules` missing the Linux Rollup optional package. Claude Code
was retried from WSL and still returned `Not logged in`; no external review
approval is claimed.

### Remaining gates before distribution/social release

- Provider-authenticated adjudication and tab/account-scoped challenge storage
  remain required before treating local AI verdicts as hosted learning proof.
- Hosted two-device mailbox acceptance, clean installer/launch verification and
  explicit conflict-choice testing remain before calling the Windows friend
  distribution slice complete.
- Hosted Dungeon state/leaderboard, friends/presence and raids remain deferred;
  Supabase was not seeded or expanded in this checkpoint.
- The existing 5173 process may still be an older checkout until the user
  chooses to restart/launch the corrected branch; the new launcher exposes a
  branch mismatch instead of silently hiding it.

Development note: while loading the final Codex textarea fix through Vite HMR,
the disposable browser runtime briefly reconnected its terminal websockets.
After HMR settled, both PTYs were `CONNECTED` and retained their marker/input
behavior through navigation and state polling. This does not occur from the
one-second campaign revision poll; use the production-built/normal launcher for
the no-reset acceptance gate. Existing user PTYs were not touched.

### Friend-ready launcher foundation — 2026-09-15

The local distribution slice now includes `tools/questlab-launch.ps1` and
`FRIEND_ONBOARDING.md`. The PowerShell entry point checks that the platform
checkout is on `feature/cloud-sync-desktop` (unless a user explicitly opts
out), validates the WSL virtual environment/frontend dependencies and selected
workspace, converts paths safely, then delegates to `ide/quest.py` with backend
reload disabled. It prints the checkout, canonical state path and workspace so
a stale long-lived runtime is visible before a session starts. It does not
kill an existing Forge process or reset either PTY.

`questlab-state runtime` is now a read-only named gateway report alongside
`authority`, `campaign` and `legacy-report`; it exposes the same runtime
identity/authority information as `/api/runtime` from a terminal. The friend
onboarding guide explicitly says that a workspace `progress.json` is legacy
evidence and must not be copied between devices. Progression continues to flow
through the state gateway and the existing compare-and-swap sync boundary.

The launcher contract and CLI routing have focused unit coverage. A clean
install, two-device mailbox sync acceptance and a packaged Tauri/native
Windows proof remain open gates; this slice does not seed Supabase, expose a
public PTY, or change the Campaign Tutor/Practice boundary.

### Custody and polling review follow-up — 2026-09-15

The authenticated Claude browser review was read-only and ran against the
OneDrive checkout plus an isolated archive; it did not edit or commit either
tree. It identified two safe code issues that are now fixed: `questlab-state`
is committed with mode `100755` for Linux clones, and `/api/runtime` now reports
the repo HEAD/upstream SHA plus ahead/behind counts. The Windows launcher refreshes
the upstream ref and refuses a stale checkout by default (with an explicit
`-AllowStaleCheckout` escape hatch), while warning rather than overwriting a
locally changed canonical save. The footer shows `CHECKOUT STALE` when the
runtime is behind its upstream branch.

The legacy `combatShell.js` overlay no longer runs its own one-second campaign
poll or refetches `/api/campaign`; it consumes the `questlab:campaign-updated`
projection emitted by React's single revision poll. This removes duplicate
campaign/git work and avoids an avoidable source of HUD/sync jumps without
remounting either PTY.

The review also confirmed the remaining custody gates: the tracked
`progress.json` is still the live offline cache, OneDrive is a third filesystem
replicator, and local verdict tokens are provider-routed but not provider-
authenticated. Those are documented/open by design. This pass does not move,
untrack or overwrite the player's save, delete the stale checkout, seed
Supabase, or claim hosted multiplayer readiness.

Post-fix gates: 55 WSL backend tests, 29 frontend tests and a green Windows
Vite production build. The K&M current-branch runtime still showed Level 2,
50 XP, 54 disposable-test coins, The Hitman at 8/8, three cleared mobs, Codex
records/field note, visible SVG HUD icons, `CHECKOUT feature/cloud-sync-desktop`
and `CONNECTED` AI/shell surfaces without a browser refresh.

### Checkout-scoped sync metadata — 2026-09-15

The local cloud-sync mailbox and friendly device label are now partitioned by
an opaque checkout namespace.
The backend derives a stable SHA-256 namespace from the platform/workspace
roots and exposes only the `checkout-<hex>` value through `/api/runtime`,
`/api/campaign` and the cheap revision probe. React resolves that value before
`SyncEngine` restores auth; the engine uses it for device IDs, labels, cursor
rows and offline outboxes. Supabase device records receive only the UUID
device ID and friendly label, never a filesystem path.

This addresses the same-origin two-checkout metadata collision without moving
or untracking the player's canonical `progress.json`, changing OneDrive
custody, or beginning Milestone C hosted state transport. Old unscoped browser
metadata is left intact and is used only when a runtime has no namespace; it is
not copied into a new checkout automatically. A new checkout therefore follows
the existing explicit revision/conflict rules instead of attributing an offline
write to the wrong cache.

Slice gates after this change: 56 WSL backend tests, 30 frontend tests,
targeted Python compilation and a green Windows Vite production build. A fresh
K&M browser smoke against a newly launched disposable runtime passed: the
runtime booted with the opaque namespace, showed Level 2 / 55 XP / 62 coins and
all five SVG stat icons, and a typed compare-and-swap state-service mutation
changed the HUD and Character to 63 coins without refresh. Quest Journal stayed
on Mob 3 The Hitman and Codex retained its validated records; both shell and AI
panes remained `CONNECTED`. The disposable runtime was stopped afterward;
current user PTYs and live saves were not restarted or modified.

### Clean Linux packaging check — 2026-09-15

To separate source regressions from the known OneDrive dependency issue, a
fresh `git archive HEAD` was extracted into `/tmp/questlab-clean-linux` (no
player save or worktree was used). WSL `npm ci` installed 84 packages and the
clean checkout's `npm run build` passed after transforming 1,344 modules. This
confirms the committed frontend builds on a Linux filesystem; F-033 remains
an environment cleanup/onboarding gate only for the shared OneDrive
`node_modules` tree, which is missing the Linux Rollup optional package. The
player checkout's dependencies were not replaced.

### Campaign loading guard — 2026-09-15

The live current-branch tab exposed a misleading failure mode when a frontend
was pointed at a stale or unavailable backend: before `/api/campaign` returned,
React rendered the starter-looking Level 1 / zero XP / zero coin defaults. That
could look like lost progress even while the canonical state remained intact.

The Forge now keeps the PTY/editor shell usable but marks the HUD and quest
banner `SYNCING`, shows an explicit campaign-waiting projection for RPG screens,
and leaves Settings available for account recovery. Character, Quest Journal,
Codex, Homestead, Dungeon and Practice do not render starter data until a real
campaign projection arrives. This is presentation-only; it does not write
progress, reset a run, or remount either PTY. Issue F-042 is recorded in the
persistent roadmap issue log.

The focused gate now passes 31 frontend tests, the full WSL backend suite passes
58 tests, and the Windows Vite build transforms 1,344 modules successfully.
Manual browser validation used click/scroll/type K&M only (no Playwright): the
loaded current runtime showed Level 2 / 50 XP / 55 coins, The Hitman at 8/8,
three cleared mobs, three Codex encounter records, and both shell/AI surfaces
`CONNECTED` without a refresh or progression mutation.

### Read-only local custody preview — 2026-09-15

The first safe part of the custody recommendation is now implemented without
changing the active save. `/api/state/custody`, the runtime health projection,
and `questlab-state custody` report the proposed opaque per-device destination,
source/destination revisions, exact file digests and a bounded status. Missing,
identical and divergent destinations are distinguished explicitly; no
newest-file heuristic is used. The preview never copies, merges, increments
campaign revision, creates a reward event or deletes the tracked source.

This remains an approval-gated migration. The default launcher still uses the
current canonical cache, the legacy workspace file remains evidence only, and
no Supabase migration/seed or hosted player-state transport was started.
The WSL backend suite is now 58 tests, the frontend suite is 31 tests, and the
Windows Vite build still transforms 1,344 modules. A clean ext4 disposable
runtime passed `npm ci`; browser click/scroll/type K&M showed the explicit
campaign `SYNCING` guard before load, the offline/local HUD after load, visible
SVG stat icons, custody JSON typed through the shell gateway, and both PTYs
`CONNECTED`. The disposable runtime and save were removed afterward.

The same clean checkout also powered two disposable local-device backends. The
custody preview produced distinct opaque namespaces and canonical paths; a
typed state-service projection mutation advanced device A to revision 1 while
device B stayed at revision 0. Both disposable backends were stopped after the
check. This is an isolation proof, not hosted sync proof, so F-039 and the
Milestone C mailbox gate remain open.

### WSL launcher dependency preflight — 2026-09-15

The guarded `ide/quest.py` launcher now detects a WSL frontend whose shared
`node_modules` tree lacks a native `@rollup/rollup-linux-*` optional package.
It exits before starting the backend/frontend pair with a direct instruction
to run `npm ci` inside WSL or use a clean Linux filesystem. The check is
read-only and does not replace dependencies, move `progress.json`, or touch
existing PTYs. A contract test covers both missing and present native package
fixtures. This bounds F-033 without pretending that the shared OneDrive tree
is clean-install safe.

Post-change gates: 59 WSL backend tests, 31 frontend tests, targeted Python
compilation, and a green Windows Vite production build transforming 1,344
modules. A real WSL invocation against the shared OneDrive checkout emitted
the same actionable message and exited before spawning its requested ports.
No Playwright was used.

### Opt-in custody gateway — 2026-09-15

The read-only custody preview now has a separately invoked migration command:
`questlab-state custody-migrate --expected-revision N --confirm
MIGRATE_LOCAL_STATE`. The gateway derives the opaque per-device destination,
copies the canonical bytes atomically, writes a bounded marker and leaves the
source JSON, campaign revision and event history unchanged. It refuses
arbitrary paths, symlinks, stale source revisions, divergent destinations and
workspace/legacy paths; identical retries are reported as `already-local`.
The operation is not called by the default launcher, and no real player save
was migrated. Full backend coverage is now 66 tests; frontend remains 31 and
the Windows Vite build remains green.

The browser replay also confirmed the stale-runtime boundary: the isolated
current-branch tab settled on Level 2 / 50 XP / 55 coins, The Hitman 8/8,
three cleared mobs, three Codex records, Homestead 55 coins, all five SVG HUD
icons and `CONNECTED` shell/AI panes. The old 5174 tab still showed its
starter/no-branch projection and was not restarted, preserving its PTY; use
the guarded launcher for a fresh current-branch session.

The guarded Windows wrapper now exposes `-MigrateLocalState`. It prints the
same custody preview, requires `MIGRATE_LOCAL_STATE` before copying, and sets
the derived local state path only for that explicit launch. A default later
launch remains on the tracked cache; no real player save was migrated.

The HUD icon regression is now hardened at the source boundary: Forge v2
renders heart, coin, streak, shield and boss SVGs directly from React instead
of emitting emoji and waiting for `uiPolish.js` to mutate the DOM. The legacy
polish bridge ignores React-owned stat values, so revision polling cannot
replace the nested SVG or its coin suffix. Frontend tests and the 1,344-module
Vite build pass; K&M showed all five icons before and after Codex navigation.

### Isolated Infinite Dungeon K&M verification — 2026-09-16

The local current-branch Dungeon contract was verified in a disposable
backend/save using browser clicks, scrolling and typing only (no Playwright).
The campaign loaded at Level 2 / 50 XP / 55 coins. `lists` focus followed by
Enter Dungeon showed a fresh run: Apprentice Coat, no trinket, one heal and
zero run coins. The visible provider bridge accepted a checkpointed answer;
the disposable state service recorded the validated verdict and Forge changed
live to the next room with a room-clear reward, new question and blank editor.
Three additional verdicts exercised code, bug-hunt and true/false rotation;
each new room started with a clean editor buffer.

The run reached REST, MARKET and encounter rooms without refresh. REST was
correctly disabled at full HP (the heal mutation is covered by the backend
tests). A Field Ration purchase showed `-12 run coins`, leaving 13, and Bank
score ended with `RUN BANKED 50 score` plus the local `#1 · lists 50 F1 ·
complete` leaderboard row. The disposable backend/frontend and temp save were
stopped and removed afterward. Existing user progress, long-lived shell/AI
PTYs and hosted state were not touched. This is local product-completeness
evidence only; hosted Dungeon persistence, cross-device resume and hosted
leaderboards remain gated by provider-auth/Milestone C acceptance.

The 2026-09-16 Claude read-only roadmap/source review confirmed that the HUD
icon and Dungeon implementations are present in source, but did not run tests
or browser checks. Its primary remaining blocker is the real hosted two-device
Supabase acceptance; provider trust findings F-001/F-009/F-010 remain open.
Custody migration therefore remains explicitly opt-in, and no new hosted
Dungeon/Codex player-state fields were added.

### Reproducible friend bundle — 2026-09-16

Slice 7 now has a guarded distribution artifact path in
`tools/questlab-package.ps1`. It validates the intended branch and rejects
uncommitted source changes, while allowing the known player-owned
`progress.json` and untracked Campaign `tutor.py` to remain in the working
tree. The actual bundle is built from `git archive HEAD`, so neither of those
dirty files can leak into the friend copy. It emits a commit manifest, a
directory bundle and a ZIP; `FRIEND_ONBOARDING.md` remains the setup contract.

The PowerShell parser and seven-test launcher contract suite passed. A real
fixture run created `QuestLab-6c61317` folder/ZIP output, confirmed onboarding
was included and confirmed root `tutor.py` was absent; the temporary artifact
was deleted afterward. This closes the source-custody portion of the local
distribution slice. It does not claim a clean-install launcher, Windows
installer or Tauri desktop acceptance, and no hosted state was seeded.

### Live RPG projection and mode-boundary K&M acceptance — 2026-09-16

The clean ext4 frontend plus a disposable copy of the reconciled save passed a
fresh click/scroll/type-only acceptance without Playwright. Forge loaded Level
2 / 50 XP / 55 coins, The Hitman at 8/8 Resolve, and connected shell/AI PTYs.
Codex search/page navigation and a typed field note produced `CODEX NOTE
SAVED`. A validated disposable reward moved the shared HUD and Homestead purse
to 105 coins; a K&M Golden Spark purchase then showed `NEW ITEM`, 25 coins and
live Equip state.

The Campaign Tutor Notebook remained the dedicated `tutor.py` surface and
Practice remained an independent no-Campaign-cost mode. A validated
`choice_flow` objective changed Resolve 8/8 → 4/8 with `OBJECTIVE VERIFIED`;
`stop_condition` then produced `MOB DEFEATED`, `+30 XP`, `+15 Coins`, the next
mob unlock and a second Codex observation. Additional disposable objective
mutations cleared the remaining mobs and visibly opened The House boss gate
with the three bounded requirements. No refresh occurred, no hidden future
prompt/answer was exposed, and neither PTY was remounted. The temporary
runtime/save was removed; user state, legacy evidence and hosted state were
untouched.

The current issue ledger now treats F-025 as fixed for new guarded launches;
only the pre-existing legacy listeners remain open as a user-controlled
restart choice.

### HUD sync layout stability — 2026-09-16

The HUD icon regression fix now also reserves a compact slot for each direct
stat pill (`min-width`, `min-height` and `white-space`) and fixed flex slots for
the nested SVG/value content. This prevents the top bar from jumping when the
first campaign revision arrives or a value changes digit length. It keeps the
React-owned monochrome SVGs, direct-child selector boundary and compact/
adventurer HUD modes unchanged. The WSL frontend suite passed 31 tests, the
full WSL backend suite passed 67 tests, and the Windows Vite build transformed
1,344 modules. No PTY or save was touched.

### Clean-install launch — 2026-09-16

A new ext4 WSL clone of pushed `8f4ec71` followed the friend setup contract:
backend venv requirements, frontend `npm ci`, and a 1,344-module Vite build.
The delegated `ide/quest.py` launch path (the target of the Windows wrapper)
ran the backend on 7360 and Vite on 5196 with reload disabled. Browser K&M
showed `feature/cloud-sync-desktop`, both shell/AI PTYs
`CONNECTED`, the starter Level 1 projection and Quest Journal. A trusted
state-service reward then changed the HUD from `0 c` to `1 c` live at revision 1
without a refresh. The disposable runtime and exact ext4 checkout were removed
afterward. This closes the clean ext4 install smoke, not the Windows friend-
machine, hosted two-device or Tauri proof.

`npm ci` also reported two dependency advisories (one low and one moderate)
in the clean-install output. This is recorded as F-050 for a targeted audit;
no forced upgrade or lockfile rewrite was applied.

### Per-tab PYR challenge isolation — 2026-09-16

The local provider bridge now partitions pending Battle, Boss and Dungeon
challenges by an opaque browser-tab id held in `sessionStorage`. The React
publisher and direct DOM enhancement fallback share the same client-id helper.
Challenge maps are expiring and provider calls locate the intended entry by its server-issued
nonce, so a second tab cannot overwrite the first tab's pending answer. The
legacy singular challenge variables remain compatibility snapshots for older
in-process callers only; they are not the lookup authority.

The focused backend test issued challenges in tab A and tab B, then submitted
tab A's Battle and Dungeon answers after tab B had issued its own challenge;
both remained bindable. Full gates passed: 68 WSL backend tests, 31 frontend
tests, Python compilation, and a Windows Vite build transforming 1,344 modules.

The browser smoke used clicks, scrolling and typing only (no Playwright). Two
disposable tabs loaded the same current-branch revision, a trusted state-service
reward moved the HUD from 0 to 1 coin without refresh, and both shell and AI
PTY labels remained `CONNECTED`. The exact temporary runtime and state folder
were removed afterward. The dirty user save, root Campaign `tutor.py`,
long-lived runtimes and hosted state were untouched. This closes local F-009;
provider-authenticated hosted adjudication remains gated by F-001/F-010.

### Targeted frontend dependency audit — 2026-09-16

The installed frontend tree was audited read-only with `npm audit --json`.
There are two package-level vulnerabilities (four GHSA advisory records: one
low and one moderate package-level result), all on Monaco's DOMPurify path; no
high or critical findings were reported. The direct editor is `monaco-editor`
0.56.0, whose package carries DOMPurify 3.4.8 and bundles the sanitizer into
the editor distribution. npm's automatic remediation is a semver-major
downgrade to `monaco-editor` 0.53.0.

Because that remediation changes the editor major line, no forced audit fix,
silent downgrade or unreviewed lockfile rewrite was applied. The current
frontend tests and production build remain green. F-050 is now a bounded
compatibility/security decision before friend distribution is called
security-clean; the audit did not touch player state, PTYs or hosted state.

A clean disposable archive was also tested with `monaco-editor` pinned to
0.53.0. Without changing the repository lockfile, its 31 frontend tests
passed, the Vite build transformed 1,293 modules, and `npm audit --omit=dev`
reported zero vulnerabilities. This is a compatibility candidate only; the
current branch remains on 0.56.0 until the semver-major editor decision is
reviewed, and npm audit does not inspect Monaco's vendored sanitizer bundle.

### F-050 decision — 2026-09-16

Claude reviewed the actual Monaco tarballs, not only npm metadata. Monaco 0.56.0
declares and bundles DOMPurify 3.4.8, so its one low and one moderate audit
finding describes code loaded by the editor. The proposed 0.53.0 downgrade
passes the suite and build but omits the dependency edge from its metadata; the
tarball still bundles DOMPurify 3.1.7, older and inside the same vulnerable
ranges. It is therefore a metadata-clean but security-worse downgrade.

The branch retains 0.56.0 as an explicit accepted low/moderate risk, with no
high/critical findings. No forced fix or lockfile rewrite was made. Revisit
only when upstream ships a Monaco bundle with DOMPurify above 3.4.12 or a
separately reviewed sanitizer patch; the friend bundle is not called
security-clean before that gate.

### Claude F-009 follow-up and coverage closure — 2026-09-16

Claude Sonnet reviewed commits `e8094c2` and `fea726e` read-only after the
scheduled availability check. It found the nonce-keyed, lock-protected
per-client maps and TTL pruning consistent across the Battle, Boss and Dungeon
routes, confirmed the DOM fallback fix was necessary, and found no current
functional regression. It noted that the prior test asserted Battle and
Dungeon isolation but not Boss isolation or the default legacy snapshot.

Those gaps are now covered by a backend regression test: the default Boss
challenge is checked against its compatibility snapshot, and tab A's Boss
submission/verdict remains valid after tab B captures its own challenge. The
full backend suite passes 69 tests; frontend tests remain at 31 and the latest
Windows Vite build transforms 1,345 modules. Claude did not edit files and
could not run the WSL suite in its sandbox; local gates remain the evidence.

### Final current-branch K&M projection smoke — 2026-09-16

The disposable 7362/5198 runtime loaded a copy of the current local save. A
click/scroll/accessibility-only browser pass (no Playwright) showed Level 2,
50 / 100 XP, 55 coins, The Hitman at 8 / 8 Resolve, three cleared mobs, the
Codex encounter records and `CONNECTED` shell/AI PTYs. A trusted state-service
reward advanced the disposable revision and changed the HUD plus reward queue
to 56 coins without a refresh. Quest Journal, Character, Homestead and Codex
continued to project the same revision. The exact temporary runtime, state
copy and browser tab were removed afterward; no user save, legacy evidence,
long-lived runtime or hosted state was touched.

### F-033 onboarding contract — 2026-09-16

The launcher contract tests now lock the friend setup boundary to native
Linux/WSL dependencies, a rerun of `npm ci` inside that checkout when Rollup's
Linux optional package is missing, and a Linux filesystem instead of a copied
cross-platform `node_modules` tree. The focused launcher suite passed 7 tests;
the full WSL backend suite passed 69 tests. The shared OneDrive limitation
remains bounded by the launcher's fail-fast check and was not papered over with
source changes.

### Cloud write provenance follow-up — 2026-09-16

Claude Sonnet reviewed the current local sync engine, state gateway and
Supabase migrations read-only. It confirmed the bounded player-state
projection is aligned across JavaScript, Python and SQL, then identified a
small provenance gap: the security-definer `save_player_state` RPC accepted a
caller-supplied `source_device_id` without checking that the UUID belonged to
the authenticated account. The same pass found loose frontend conflict
classification based on arbitrary message text and an unreachable revision-
zero push branch.

The new migration
`supabase/migrations/20260916000100_player_state_device_ownership.sql` now
requires an account-owned `public.devices` row before any player-state write.
The fake-cloud test boundary enforces the same rule, the frontend accepts
only SQLSTATE `40001` or HTTP `409` as a sync conflict, and the dead branch was
removed. The Supabase migration is committed for the next approved deploy but
was not applied or seeded in this checkpoint. The frontend suite passes 33
tests, including foreign-device rejection and strict conflict handling; the
SQL test is updated but remains unapplied pending the real Milestone C gate.

Claude's follow-up review of commit `6b301fa` found no correctness bugs and
marked the slice safe to keep. The review confirmed that the replacement RPC
retains the bounded validator and grants, that SQLSTATE `40001`/HTTP `409` are
the reachable conflict signals, and that the fake-cloud and SQL regressions
match the migration history. It also records the remaining evidence boundary:
the migration has not been applied to Supabase, the SQL test has not been run
against Postgres, and the real two-device authenticated acceptance is still a
Milestone C gate.

### Fresh roadmap checkpoint review — 2026-09-16 02:06

The new read-only snapshot records the reconciled local campaign at revision 2
(Level 2, 50/100 XP, 150 lifetime XP, 55 coins, three cleared Blackjack mobs,
The Hitman at 8/8 and three Codex encounter records). Claude Sonnet reviewed
that snapshot against the handoff, roadmap and current source and found no new
local defect. It recommends no further local gameplay expansion before
Milestone C; the remaining local decision is the explicit F-039 save-custody
choice for tracked `progress.json`/OneDrive custody.

The next evidence package is the hosted eight-step two-device acceptance,
including offline/reconnect CAS conflict handling, both explicit conflict
resolutions and PTY survival, followed by Milestone D private/offline avatar
acceptance. The pending ownership migration remains committed but unapplied;
this checkpoint did not sign in, seed Supabase or mutate hosted state.

### Hosted migration contract coverage — 2026-09-16

Because the ownership migration remains unapplied by policy, six local
repository contract tests now keep the hosted SQL and executable RLS fixtures
aligned. They verify the `public.devices`/`auth.uid()` guard occurs before
validation and row locking, preserve the authenticated-only RPC grant, and
cover both the player-state foreign-device path and the private account-scoped
avatar bucket, account-private identity rows and bounded player-state values.
The focused contract suite passes 6/6; it performs no Supabase connection or
hosted write.

The post-change verification also passes the full WSL backend suite (75 tests),
the frontend suite (33 tests), Python compilation, `git diff --check`, and the
Windows Vite production build (1,345 modules). A first full-suite run exposed
one transient websocket cancellation; the immediate rerun passed cleanly. No
browser/runtime or PTY was restarted for this documentation/test-only change.

### Current state snapshot — 2026-09-16 02:24

`GAME_STATE_SNAPSHOT_2026-09-16_0224.md` re-read the canonical working-tree
save after the avatar-contract slice. Revision 2 is unchanged: Level 2,
50/100 current XP, 150 lifetime XP, 55 coins, three defeated Blackjack mobs,
The Hitman at 8/8 Resolve and three Codex encounter records. The read-only
capture confirms no unsupported equipment, mastery, companion or interview
rewards were inferred and that the dirty save/notebook boundary remains intact.

### K&M projection recheck — 2026-09-16 02:29

Using the in-app browser's accessibility/click surface only (no Playwright), a
disposable tab on the current-branch runtime at `127.0.0.1:5174` settled on
the canonical projection without a browser refresh. The visible HUD showed
Level 2, 50/100 XP and 55 coins; the heart, coin, flame, shield and sword SVG
icons were visible rather than nested pills. Navigation in the same tab showed
the Quest Journal with three defeated mobs and The Hitman at 8/8 Resolve, the
Codex with three encounter records, Character with 55 coins, and Homestead with
the same 55-coin purse. The raw CLI terminal remained `CONNECTED`; the prior
disposable run also recorded the AI PTY as `CONNECTED` through the same flow.

The first accessibility snapshot from this long-lived development runtime
briefly showed its old starter bootstrap before the current projection landed;
the subsequent no-refresh state was canonical. This remains the documented
F-035/F-025 dev-HMR/stale-runtime caveat, not hosted-state evidence. No
long-lived runtime or PTY was restarted.

### Legacy HUD loading hardening — 2026-09-16 02:37

The legacy `App.jsx` fallback was hardened so a campaign that has not yet
arrived from the revision-aware state service cannot flash starter Level 1 / 0
XP / 0 coins values while the current projection is loading. It now presents a
small `SYNCING`/campaign-state placeholder, gates the dependent banner and
activity values, and renders the same monochrome React-owned heart, coin,
flame, shield and sword SVG icons used by the current Forge projection. The
existing direct-child `.top-stats > span` rules keep the icon/value spans from
becoming nested pills. This is a fallback guard only; it does not create a
second state authority or alter either save file.

The post-change frontend suite passes 33/33 tests and the Windows Vite build
passes after transforming 1,345 modules. The change is committed as
`304fe76` and pushed to `feature/cloud-sync-desktop`. `progress.json` and the
untracked root `tutor.py` remain deliberately unstaged and untouched.

### Earlier 5174 smoke superseded — 2026-09-16 02:38

An earlier disposable-tab capture on `127.0.0.1:5174` appeared to settle
without a refresh, but the later source inspection in the 02:52 snapshot
confirmed that this long-lived WSL-mounted Vite process was serving an older
cached AppV2 transform. That capture is retained as stale-runtime evidence
only and must not be used as current-branch UI proof. The branch-aware 5177
K&M run below is the authoritative post-change acceptance.

The active AppV2 path also keeps the loading coin placeholder as a bare `—`
until the campaign revision arrives, then switches atomically to the formatted
`Nc` value. This removes the last loading-only suffix width change. The
regression is included in the 33-test frontend suite and the follow-up commit
is `ecffa40`.

### Current state and branch-aware K&M snapshot — 2026-09-16 02:52

`GAME_STATE_SNAPSHOT_2026-09-16_0252.md` re-read the canonical local state at
revision 2 (Level 2, 50/100 XP, 150 lifetime XP, 55 coins, The Hitman 8/8,
three defeated mobs, 38% Blackjack progress and three Codex records). It also
records a newly confirmed runtime boundary: long-lived 5174 has the current
OneDrive cwd but serves an older cached AppV2 transform, so it remains a
known F-025/F-035 stale-runtime process and was not restarted.

A fresh ext4 clone at branch `feature/cloud-sync-desktop`, HEAD
`71fdb9e1dedf3aee0474ac7c259b6cc6b420c46e`, served the current SVG/loading
source on 5177/7343. Pure K&M acceptance there observed revision-aware
Resolve reduction, reward/achievement/next-mob presentation, Journal/Codex
projection and connected shell/AI PTYs without a refresh or Playwright. The
disposable runtime was closed afterward; user save files and long-lived PTYs
were untouched.

### Claude Sonnet read-only review — 2026-09-16 03:01

Claude reviewed HEAD `66e2d37`, the snapshot, handoff, roadmap, issue/report
ledger and HUD/state source without editing or mutating anything. It found no
correctness bugs in the `campaignReady` loading guard, React-owned SVG stats,
`uiPolish.js` bridge, or branch-aware K&M evidence. It rated the stale 5174
disclosure as accurate, while keeping F-025/F-035 open because there is not
yet an automated source/HMR drift tripwire. It also noted only a cosmetic
legacy/current coin-construction difference. Claude recommends no release to
main until hosted Milestone C and the explicit F-039 save-custody decision;
Milestone D and Tauri remain behind those gates.

Claude's note about a large modified-file count was a WSL presentation
artifact, not additional semantic work: the Windows checkout reports only the
user-owned `progress.json` plus untracked `tutor.py`, and WSL
`git diff --ignore-space-at-eol --stat` likewise leaves only `progress.json`.
No cross-shell line-ending normalization or infrastructure change was made.

### Read-only K&M runtime preflight — 2026-09-16 03:11

The new `tools/questlab-km-preflight.ps1` gate is deliberately read-only: it
checks the expected branch and local upstream ref, backend repository identity,
canonical/legacy state authority, current campaign revision, and served
`AppV2` loading/SVG markers using HTTP GETs only. It does not fetch, mutate the
save, restart a process, or touch either PTY. Against the known stale
long-lived `7333/5174` runtime it failed closed because that backend did not
expose a matching repository HEAD. A fresh ext4 clone of
`feature/cloud-sync-desktop` at `5a051fb84cb2192e5cab42f3bf8e5df14f7c5a32`
passed GREEN on `7344/5178`, reporting canonical revision 0 and a distinct
non-authoritative workspace legacy path; after the disposable acceptance
mutation it still passed at revision 2.

The pure in-app-browser K&M run on that branch-matched runtime started at the
visible `SYNCING` placeholder and settled without refresh. A validated
state-service objective changed The Empty Table Resolve from 4/4 to 2/4 and
rendered an objective toast. A second validated objective defeated it; the
same tab then showed `25/100 XP`, `10c`, the `MOB DEFEATED`, `NEXT ENCOUNTER`
and `First Blood` notifications, The Dealer's Hand unlocked in the Quest
Journal, the defeated encounter in Codex, and the same coins/equipment in
Character and Homestead. Shell and raw AI PTYs remained `CONNECTED`. No
Playwright, browser refresh, long-lived runtime restart or user-save mutation
was used. The isolated runtime was closed after capture.

The focused launcher contract suite is 8/8, the full WSL backend suite is
76/76, and the PowerShell preflight script parses successfully. The preflight
is now a manual K&M release gate for catching the F-025/F-035 stale-mounted
Vite condition before relying on browser evidence.

### Current snapshot and Claude roadmap plan — 2026-09-16 03:15

`GAME_STATE_SNAPSHOT_2026-09-16_0315.md` captures the live canonical
projection at revision 2: Level 2, 50/100 XP, 150 lifetime XP, 55 coins,
100/100 HP, three cleared Blackjack mobs, The Hitman at 8/8 Resolve, 38%
project progress, three Codex encounter records and First Blood. Equipment,
companion and mastery fields are recorded exactly as present; unsupported
legacy rewards remain un-inferred. The snapshot also records the dirty
`progress.json`/untracked `tutor.py` boundary and the older 7333/5174 runtime
that must not be used as current-branch acceptance evidence.

Claude Sonnet then reviewed the snapshot, roadmap, handoff, implementation
report and issue ledger read-only. The resulting dependency-ordered plan is
`ROADMAP_CLAUDE_IMPLEMENTATION_PLAN_2026-09-16_0315.md`. It confirms local
Slices 0–6 are implemented, Slice 7 is partial, and hosted Milestone C is the
next real gate. It keeps device-ownership migration, F-039 save custody,
avatar acceptance, Tauri, public web and Slice 8 behind explicit approvals and
defines exact automated-test and pure K&M stages for each. No hosted project,
save, runtime or PTY was changed during the review.

The post-plan regression pass at 03:26 reran the full WSL backend suite
(76/76), the frontend suite (33/33), and the Windows Vite production build
(1,345 modules; successful with the existing chunk-size warning). The run
left the working tree boundary unchanged: only user-owned `progress.json` is
modified and root `tutor.py` remains untracked.

### Current-HEAD K&M checkpoint — 2026-09-16 03:29

A fresh ext4 clone of the pushed HEAD `26ad97b24b8b0e9167d525008a8c660775236db4`
passed the read-only preflight on `7345/5179` at revision 0. Pure K&M opened
the tab in `SYNCING`, then settled without refresh to the starter projection
with both shell and raw AI PTYs `CONNECTED`. Two validated state-service Battle
objectives advanced the disposable revision 0→1→2: Journal Resolve moved
4/4→2/4 with an `OBJECTIVE VERIFIED` toast, then the mob clear showed
`25/100 XP`, `10c`, `MOB DEFEATED`, `NEXT ENCOUNTER`, and `First Blood`.
The same tab confirmed The Dealer's Hand in the Journal, the defeated record in
Codex, and matching Character/Homestead coin projections. No Playwright,
refresh, long-lived runtime restart, user-save edit or hosted write occurred;
the exact disposable runtime was closed and removed afterward.

### Claude checkpoint review — 2026-09-16 03:31

Claude Sonnet reviewed HEAD `0722036`, the snapshot, roadmap plan, report and
issue ledger read-only. It found the current K&M evidence, 76/33/build counts,
and canonical/legacy custody statements internally consistent. It explicitly
distinguished the disposable revision-2 starter state from the real canonical
revision-2 restored save, found no contradiction, and recommended holding
mainline/hosted work behind F-039 and Milestone C. It noted one minor evidence
gap: the preceding K&M run used docs-only parent `26ad97b`; a fresh exact-tip
preflight then passed GREEN at `0722036` on `7346/5180`, revision 0, with the
canonical and legacy paths distinct. No runtime, PTY, save or hosted state was
changed by the review or preflight.

### Friend bundle custody smoke — 2026-09-16 03:35

`tools/questlab-package.ps1` was rerun against committed HEAD
`4f6a98fd44b2f3cfd1bcc6dd48d9915d3b7fbb21` while the working tree still held
the user's dirty `progress.json` and untracked `tutor.py`. The package and ZIP
were created in an exact disposable temp directory, the manifest identified
the expected branch/HEAD, and inspection confirmed `tutor.py` was absent while
the committed baseline `progress.json`, snapshot and plan were present. The
temporary bundle was removed after inspection. This is committed-source
distribution evidence only; it is not a Windows installer, Tauri or hosted
two-device proof.

### Current-tip Dungeon and Practice K&M — 2026-09-16 03:48

A fresh ext4 clone of pushed HEAD `9b7c10f589923708593b20e53d833cf349448ab7`
was served on backend `7348` and frontend `5182`. The read-only preflight was
GREEN at campaign revision 4 and confirmed the canonical clone save plus a
distinct non-authoritative workspace legacy path. The previous disposable
frontend/backend pair was closed after it was found to be proxying an older
runtime; no long-lived process or user-owned save was touched.

Pure in-app-browser K&M (no Playwright, no refresh) then:

- opened Infinite Dungeon, started a fresh starter-loadout run, and observed
  the state-service `DUNGEON RUN STARTED` reward presentation;
- typed a Lists/random-selection answer into `dungeon.py` and saved a
  checkpoint through the gateway;
- applied one disposable provider-bound state-service verdict using the exact
  nonce/submission/digest binding. Revision 2 → 3 changed the live UI to Floor
  1 · Room 2, score 10, run coins 5, a new multiple-choice question and an
  empty `dungeon.py` buffer. The UI showed `LAST RESULT CORRECT` with `+10
  score · +5 coins`;
- opened Practice, selected Lists, and requested a Tier 1 multiple-choice
  drill. The live Practice projection showed one history session and the
  explicit `no Campaign or Dungeon rewards` boundary. The campaign player
  stayed Level 1, 0 XP, 0 coins while the Dungeon score remained 10/5;
- kept the shell and raw AI PTY indicators connected during the visible
  checks. A disposable Codex update prompt appeared; the update process was
  stopped and the disposable runtime was removed after capture.

The run proves the local mode boundary and blank-buffer rotation against one
current-tip backend/frontend pair. Hosted Dungeon persistence, hosted
leaderboards, and provider-authenticated adjudication remain behind F-018 and
Milestone C; this disposable verdict is not a claim of hosted AI validation.

### Current campaign snapshot — 2026-09-16 03:53

`GAME_STATE_SNAPSHOT_2026-09-16_0353.md` is a fresh read-only capture of the
running canonical projection at revision 2. It confirms the reconciled Level
2 / 50 XP / 55 coin campaign, three cleared Blackjack mobs, The Hitman at
8/8 Resolve, 38% project progress, First Blood and three Codex encounter
records. It also records that the existing 7333/5174 runtime is stale for
branch-aware acceptance and that the user's dirty `progress.json` and
untracked `tutor.py` remain untouched.

The focused launcher/HUD contract suite is now **9/9**; the added regression
asserts that stat pills stay direct-child scoped, nested SVG/value spans are
reset to non-pill styling, and `uiPolish.js` only mutates direct stat nodes.

After restoring the missing `httpx2` package in the Quest Lab WSL test venv
(environment-only; no repository or save change), the full backend suite is
**77/77** and the frontend suite remains **33/33**.

The committed-source friend bundle smoke was rerun at HEAD `7e1a5e2`: the
manifest carried that exact source SHA, `progress.json` was present from
committed source, and the user's untracked `tutor.py` was absent. The bundle
and ZIP were removed from the disposable Temp directory after inspection.

The Windows production build also remains green: Vite transformed 1,345
modules and completed in 36.25s with only the existing large-chunk warning.

The K&M preflight now also probes `/api/runtime` through the frontend and
requires its branch, HEAD and canonical/legacy paths to match the direct
backend probe. A clean ext4 runtime at `9dfb1cd` passed this paired-identity
gate on `7349/5183` at revision 0; the disposable runtime was removed after
capture. This closes the evidence gap exposed by a mismatched disposable Vite
proxy while keeping F-025's old long-lived runtime open and untouched.

At 04:10 the current in-app browser tab on port `5174` was inspected without a
refresh using the K&M surface. It served the older Level 1 / 0 XP UI and the
legacy runtime health response, so its empty stat pills and starter campaign
are stale-runtime evidence rather than a current state-service projection.
The tab was closed; the long-lived backend/frontend/PTys and both save paths
were left untouched. Use the paired preflight before accepting any browser
result from a runtime port.

The exact pushed tip `d97bb2c` was also checked in a clean ext4 disposable
clone at backend `7351` / frontend `5186`. The paired preflight passed at
revision 0. In-app-browser K&M showed the React SVG heart, coin, flame, shield
and sword icons as visible nested content (not pills), both terminal labels
connected, and a gateway learning-event mutation advanced revision 0→1; the
HUD projection updated in place without a refresh. The disposable runtime and
state were stopped and removed.

Claude Sonnet's 04:24 read-only audit confirmed the Stage 1–4 evidence and
identified no unsupported release claim. It did flag the need to distinguish
real save changes from WSL CRLF/LF noise; the 04:20 snapshot now records that
boundary. A small local guard was added after the review: if the frontend sees
the legacy runtime health shape without branch/HEAD/state-authority identity,
the Forge footer says `RUNTIME STALE · use current launcher`. This is passive,
does not remount or reconnect either PTY, and does not alter any save or cloud
state.

### Current-tip regression rerun — 2026-09-16 04:35

The pushed `0d83bd6` documentation checkpoint was revalidated without touching
the player save or long-lived runtimes. The project WSL virtualenv ran the full
backend suite at **77/77**; the frontend suite passed **33/33**; Python
`compileall` passed; and the Windows Vite build passed after transforming 1,345
modules. The only build output is the existing large-chunk advisory. An
initial system-Python invocation lacked FastAPI/Pydantic and was not treated
as a product failure; subsequent project-venv evidence is authoritative.

### Fresh snapshot and Claude dependency plan — 2026-09-16 04:40

`GAME_STATE_SNAPSHOT_2026-09-16_0438.md` is the current read-only campaign and
runtime baseline. Claude Sonnet's follow-up plan is versioned at
`ROADMAP_CLAUDE_IMPLEMENTATION_PLAN_2026-09-16_0438.md`. It confirms that the
local slices and fake-cloud boundaries are implemented, while real Windows
friend launch, F-039 custody choice, hosted two-device sync, hosted avatar,
Tauri, public web and social privacy proofs remain ordered gates. The review
made no edits, ran no commands against the game, touched no PTY and performed
no hosted operation.

### Post-plan regression rerun — 2026-09-16 04:45

After the snapshot and Claude plan were committed, the project WSL virtualenv
again passed **77/77** backend tests and the frontend suite passed **33/33**.
Custody migration tests remained isolated to temporary fixtures; the real
canonical save, legacy evidence, long-lived PTYs and stale runtime were not
changed.

The current `HEAD` archive was inspected without creating a persistent bundle:
113 committed entries included the baseline `progress.json` and
`FRIEND_ONBOARDING.md`, while the user's untracked `tutor.py` was absent. This
confirms the friend-bundle custody boundary at `444fef7`; a real second-Windows
launch is still required before Slice 7 can be called complete.

Read-only listener inspection also found legacy 7332–7334/5173–5175 runtimes
and a branch-aware disposable 7341 backend whose canonical path is a temporary
`/tmp/questlab-browser-final/progress.json`. None was restarted or treated as
current-user evidence; branch-aware paired preflight remains the required K&M
gate for avoiding stale or temporary projections.

### Codex evidence projection and current-pair K&M — 2026-09-16 05:06

Codex now indexes validated encounter text in its search and shows the
state-service-provided weakness/pattern, verified-result/evidence and optional
interview-history sections for the selected encounter. Legacy records without
`page_id` still resolve through the existing concept fallback; no reward,
mastery or Resolve values are invented in React. The focused frontend source
regression covers this projection.

The exact current source `f8634b4` passed paired K&M preflight on backend
`7354` and frontend `5190`, revision 2. Using only in-app-browser accessibility
actions (no Playwright), the test searched `legacy`, searched `append`, cleared
the filter, opened Lists & collections, and verified its definition/example,
Dealer's Hand result, and the new insight headings without refreshing. A
Forge screenshot showed the heart, coin and streak SVG icons visibly rendered
inside their stat pills. The disposable UI/backend were shut down after the
run; long-lived PTYs and canonical/legacy state were left untouched. This
isolated disposable backend rejected PTY websockets by design, so PTY survival
continues to rely on the earlier paired-runtime K&M evidence.

### Current game snapshot before local distribution — 2026-09-16 05:10

`GAME_STATE_SNAPSHOT_2026-09-16_0510.md` is the current read-only campaign
baseline at pushed HEAD `794c1a2`. It confirms canonical revision 2 with Level
2, 50/100 XP, 150 lifetime XP, 55 coins, three cleared mobs, The Hitman at
8/8 Resolve, First Blood and three validated Codex encounter records. The
canonical/legacy hashes remain distinct and the protected local save plus
untracked Campaign `tutor.py` remain untouched. The evidence ordering still
points to real second-Windows distribution and the F-039 custody choice before
any hosted Supabase, avatar, Tauri, public or social work.

### Local distribution custody and launcher gate — 2026-09-16 05:11

The current HEAD `794c1a2` was packaged through
`tools/questlab-package.ps1`. The manifest recorded the exact SHA; committed
baseline `progress.json` was present, while untracked Campaign `tutor.py` and
the dirty player save were excluded. The temporary package was removed after
inspection.

The Windows launcher was exercised on disposable ports `7355/5191`. It
reported the expected branch/upstream/canonical path and stable PTY mode,
warned about the protected local save, then failed closed before spawning on
the known OneDrive WSL dependency boundary (missing Linux Rollup optional
package). No disposable listener remained and no long-lived PTY or save was
changed. A clean WSL/Linux dependency install remains the prerequisite for
real second-Windows K&M acceptance.

### Exact current-tip live progression K&M — 2026-09-16 05:26

The paired current-source preflight was GREEN at `c4b08da` on disposable
backend `7356` / frontend `5192`, with the starter test revision at 0. Pure
in-app-browser keyboard/mouse actions only (no Playwright, no browser refresh)
used valid provider-bound state-service requests typed through the shell PTY.
The Empty Table Resolve changed 4/4 to 2/4 live; the next valid objective then
cleared it and advanced the disposable revision 0 to 1 to 2. The live HUD
showed 25 XP / 10 coins and queued the validated mob-defeat, next-encounter
unlock and First Blood notifications. Quest Journal showed the cleared mob,
Dealer's Hand 6/6, progress 12% and weekly progress 1/2. Codex showed eight
records indexed with validated result/evidence, Character showed the live
XP/coins and achievement, and Homestead showed the live purse. Both the Forge
terminal and AI PTY stayed CONNECTED throughout.

The disposable clone, runtime and mutated starter save were stopped and
removed. The user's canonical save, legacy evidence and untracked Campaign
`tutor.py` were not touched. This validates the live projection path at the
exact pushed tip without fabricating a canonical migration. See
`GAME_STATE_SNAPSHOT_2026-09-16_0526.md` and the issue log for the bounded
evidence and remaining local-distribution/hosted gates.

### Current pushed-tip regression gates — 2026-09-16 05:32

The pushed documentation checkpoint `8cdd15136ead00d40777feb9fca8ed9770d54fe3`
was rechecked without changing the player state. The project WSL virtualenv
passed **77/77** backend tests and `compileall -q ide`; the Windows frontend
passed **33/33** tests and Vite built **1,345 modules** with only the existing
large-chunk advisory. No save, Campaign `tutor.py`, PTY or hosted resource was
changed. This confirms the exact-tip K&M evidence remains applicable because
the intervening commits are documentation-only.

### Current ext4 distribution K&M — 2026-09-16 05:37

A fresh ext4 clone of pushed `e1d8a03` installed the backend requirements and
frontend dependencies with `npm ci`, then built **1,345 modules**. The
stable-PTY runtime served the clone on `7357/5193`; paired preflight was
GREEN at revision 0 and confirmed the canonical/legacy authority split.

Using only in-app-browser click/scroll/type actions, the shell issued valid
state-service Battle requests. Resolve changed **4/4 → 2/4** with an
`OBJECTIVE VERIFIED` toast; the next valid objective produced live **25 XP /
10 coins**, mob-defeat/next-encounter/First-Blood notifications, and revision
polling updated the UI without refresh. Quest Journal showed Dealer's Hand
6/6, Codex showed the encounter record and verified evidence, Character and
Homestead showed the same live projection, and both shell and AI PTYs stayed
CONNECTED. The runtime, clone and disposable save were stopped and removed;
the user's canonical save and Campaign notebook were not touched. This is a
clean Linux distribution proof, not the still-open real Windows friend-machine
gate.

The refreshed read-only baseline is `GAME_STATE_SNAPSHOT_2026-09-16_0539.md`;
it confirms the canonical revision-2 Level 2 save and the protected
`progress.json`/`tutor.py` custody boundary after this evidence run.

### Current bundle custody recheck — 2026-09-16 05:40

The committed-source packager was rerun at pushed HEAD `6629364` into an
exact temporary directory. The bundle contained committed `progress.json` and
the manifest, excluded the untracked Campaign `tutor.py`, and was removed
after inspection. No live save, notebook, PTY or hosted resource was changed.

### Reward authority hardening — 2026-09-16 05:45

The frontend reward queue had a hardcoded boss `+100 XP` fallback. That was
removed: boss XP is now displayed only when the validated state-service event
contains `boss_reward_xp` or `reward_xp`. The focused regression passed,
backend passed **77/77**, frontend **34/34**, compileall passed and Vite built
**1,345 modules**. This preserves the rule that React renders validated events
and never invents progression rewards.

### Post-fix exact-tip K&M — 2026-09-16 05:47

A clean ext4 clone at pushed HEAD `6095aaa` passed paired preflight on backend
`7358` / frontend `5194`. Using only in-app-browser keyboard/mouse actions
(no Playwright and no refresh), the Forge showed both shell and AI PTYs
`CONNECTED`; a shell-typed valid state-service Battle objective produced an
`OBJECTIVE VERIFIED` toast and live Resolve **4/4 → 2/4**. The exact-tip
runtime, clone and disposable save were stopped and removed. The canonical
Level 2 save and Campaign `tutor.py` were untouched. This smoke confirms that
the live projection path remains healthy after the validated reward-rendering
hardening.

### Claude review and rollback hardening — 2026-09-16 06:03

Claude Opus performed a read-only review of the pushed tree and found no P0 or
P1 findings. The two P2 items are fixed: Git preflight now handles missing
remote refs without null `.Trim()` failures, and a lower campaign revision is
treated as a deliberate new authority with a fresh event baseline rather than
leaving revision polling stuck on stale UI. A P3 numeric guard also prevents an
explicit null boss reward from becoming `+0 XP`. Focused frontend tests pass
**35/35**, backend **77/77**, PowerShell parsing passes and Vite builds **1,345
modules**.

### Current-tip K&M after review fixes — 2026-09-16 06:04

A disposable ext4 clone at pushed HEAD `c8dba22` ran on backend `7359` and
frontend `5195`. Pure in-app-browser keyboard/mouse actions (no Playwright and
no refresh) visibly showed the monochrome heart, coin, streak, shield and boss
icons; both shell and AI PTYs stayed `CONNECTED`; a shell-typed state-service
Battle submission/verdict changed Resolve **4/4 → 2/4** and added the validated
`OBJECTIVE VERIFIED` reward card. The runtime, clone and disposable workspace
were stopped and removed; canonical `progress.json` and Campaign `tutor.py`
were untouched.

### Preflight cross-shell hardening — 2026-09-16 06:06

The read-only Git probes now use quiet `rev-parse --verify` exit status without
native stderr redirection, avoiding the Windows PowerShell 5.1
`$ErrorActionPreference='Stop'` edge case identified in review. PowerShell
parsing and the focused frontend suite remain green (**35/35**); no runtime,
save or PTY was touched.

### Snapshot and fallback roadmap plan — 2026-09-16 06:08

The read-only checkpoint `GAME_STATE_SNAPSHOT_2026-09-16_0608.md` records the
current branch, canonical revision/state, hashes and dirty-file boundary. A
new Claude Sonnet planning request exceeded the five-minute response window;
the earlier Claude plan remains valid and the dependency-ordered fallback
matrix is recorded in `ROADMAP_EXECUTION_PLAN.md`. No code, runtime, save or
PTY was changed by the timeout.

### Stale runtime audit — 2026-09-16 06:09

Read-only probes found legacy listeners on `5173`, `5174`, `7332`, `7333` and
`7334`. Their `/api/runtime` responses lack `repo_git`, `expected_branch` and
`state_authority`, so they are not current-branch acceptance evidence. `5180`
was not listening. No existing process, PTY or save was restarted or killed;
the safe path remains a guarded launch from the current checkout.

### Windows launcher identity hardening — 2026-09-16 06:20

The guarded launcher now handles a checkout with no upstream ref without a
null `.Trim()` failure. It resolves the branch upstream with `for-each-ref`,
checks HEAD/upstream hashes with quiet Git probes and fails closed when either
identity is unavailable. Launcher contract tests pass **9/9** and PowerShell
parsing passes. No launcher, save or PTY was started or changed.

### Post-launch-fix regression — 2026-09-16 06:22

The full WSL backend suite passed **77/77**, frontend **35/35**, Python
`compileall -q ide` passed, launcher contracts **9/9** passed, PowerShell
parsing passed and Vite built **1,345 modules**. Read-only Git identity checks
resolved the current branch, upstream and equal HEAD hashes. No canonical or
legacy save, long-lived runtime or PTY was touched.

### Current-tip launcher checkpoint K&M — 2026-09-16 06:25

A fresh ext4 clone at pushed HEAD `55acb0b` installed its WSL virtualenv and
frontend dependencies, then served the stable-PTY runtime on backend `7361`
and frontend `5197`. Pure in-app-browser click/type/scroll actions only (no
Playwright and no refresh) showed the current branch, visible monochrome HUD
icons and both terminal surfaces `CONNECTED`. A shell-typed state-service
Battle context/submission/verdict changed The Empty Table Resolve **4/4 →
2/4**; Quest Journal then showed **2/4** and the validated `OBJECTIVE VERIFIED`
reward card. The clone, runtime and mutated starter save were removed; the
canonical save, legacy evidence, Campaign `tutor.py` and long-lived PTYs were
untouched.

### Narrow Claude roadmap refresh — 2026-09-16 06:30

Claude Sonnet's read-only refresh confirmed the real Windows friend-machine
launch as the only locally implementable roadmap gap. It kept F-039 as an
owner decision and Milestones C–F, hosted Dungeon, provider authentication and
Slice 8 behind their existing approvals. Stale mid-document test/snapshot
references were corrected in `ROADMAP_EXECUTION_PLAN.md`; no code, save,
runtime or PTY was changed.

### Persistent state snapshot — 2026-09-16 06:31

`GAME_STATE_SNAPSHOT_2026-09-16_0631.md` records the read-only continuation
checkpoint: canonical/legacy hashes, the reconciled Level 2 / 50 XP / 55 coin
state, three cleared Blackjack mobs with The Hitman at 8/8, three Codex
encounter records, green 77/35/9/build gates, current-tip pure K&M evidence
and the remaining Windows/hosted approval gates. No save, runtime or PTY was
changed.

### OneDrive WSL dependency caveat — 2026-09-16 06:37

The guarded launcher was exercised on unused ports `7370/5200` and correctly
refused the OneDrive-mounted dependency tree because Linux Rollup was absent.
Both WSL `npm ci` and `npm install --include=optional` hit `EIO`/`ENOENT` while
replacing the mounted Windows `esbuild` package. The preflight remains strict;
the documented clean Linux/ext4 checkout path is the validated local launch
route. No tracked file, save, runtime or PTY changed.

### Claude Sonnet local-slice review — 2026-09-16 06:47

Claude Sonnet performed a read-only review of the current branch, launch
scripts, handoff, roadmap and persistent logs. It found no P0 correctness
issues and confirmed that the local slice/authority/revision/event/PTY claims
are coherent. It reiterated that F-039 tracked-save custody remains an owner
decision, F-033 should explicitly forbid WSL dependency installs in the live
OneDrive tree, and CRLF/LF noise remains a review-process issue. The proposed
`.gitattributes` normalisation is deliberately deferred because it would
rewrite many tracked files while protected `progress.json` and Campaign
`tutor.py` are dirty; it requires a separate approved change window. The
recommendation is to proceed only with the local Slice 7 Windows/ext4 launch
gate and hold hosted/Tauri/social work behind approvals. No code, save,
runtime or PTY was changed by the review.

### Current Windows launcher preflight — 2026-09-16 06:50

After restoring the ignored Linux Rollup/esbuild packages from temporary
registry archives (no tracked source change), the guarded launcher served the
current checkout on `7370/5200` with a distinct disposable quest workspace.
`questlab-km-preflight.ps1` passed GREEN at HEAD
`4f5bbaaa04c2ad2f9f7219f6b210a30c76a1ae4d`, revision 2, with distinct
canonical/legacy paths. Pure K&M navigation (no refresh, no Playwright) showed
Level 2 / 50 XP / 55 coins, The Hitman 8/8, three cleared mobs, three
validated Codex encounter records, visible monochrome HUD SVG icons and both
PTY labels `CONNECTED`. No mutation was issued because this runtime pointed
at the protected canonical save; earlier disposable current-tip K&M covers the
reward/Resolve mutation. The runtime and workspace were closed and cleaned;
long-lived runtimes and PTYs were untouched.

### Friend onboarding guardrails — 2026-09-16 07:01

Pushed `5f678e7` with a documentation/test-only hardening slice. Friend setup
now prefers an Ubuntu/ext4 checkout, forbids WSL `npm install`/`npm ci` against
the live OneDrive-mounted frontend dependency tree, and requires a separate
quest workspace for the canonical-versus-legacy path preflight. The launcher
contract test asserts both guardrails. No code, save, runtime or PTY changed;
the protected `progress.json` and Campaign `tutor.py` remain unstaged.

### Claude Sonnet roadmap plan — 2026-09-16 07:14

Authenticated Claude Sonnet re-audited the current handoff, 07:05 snapshot,
roadmap, issue log, source and tests in read-only plan mode. It found no P0/P1
correctness issues and returned the dependency-ordered implementation and K&M
acceptance plan persisted at
`ROADMAP_CLAUDE_IMPLEMENTATION_PLAN_2026-09-16_0705.md`. The review identified
only documentation precision around the internal-only `system` actor and the
effective Campaign `tutor.py`/Practice boundary, plus a missing CI automation
boundary note now tracked as F-052. Stage A still needs a real second-Windows
environment and the explicit F-039 custody decision; no hosted, Tauri, public
or social operation was authorized or performed.

### Disposable K&M state-custody incident — 2026-09-16 07:23

During a fresh browser-only Dungeon check, a separate workspace was supplied
but the launcher still correctly used the protected canonical cache. Starting
the run and saving a 33-byte editor buffer therefore created state-service
events at revisions 3 and 4. I stopped that runtime and used the existing
internal `dungeon_record_death` action at revision 5 with the explicit reason
`ephemeral browser acceptance cleanup; no reward`; no direct JSON edit, reward,
Campaign/Codex/equipment change or PTY reset occurred. The player state remains
Level 2 / 50 XP / 55 coins / The Hitman 8/8. The dead zero-score test run is
retained for audit and does not block a fresh run. F-053 requires all future
mutating disposable K&M sessions to opt into an explicitly confirmed isolated
local cache before interaction; a separate workspace alone is not enough.

### Isolated K&M projection acceptance and custody-guard correction — 2026-09-16 07:38

The first attempt to exercise `-RequireIsolatedState` exposed a real
PowerShell portability defect: a two-character `'\\'` literal was passed to
`TrimEnd`, and the separator replacement would not normalize a single
backslash. Both literals are now single-character PowerShell strings and the
launcher contract asserts the corrected forms; the script parses and the
preflight passes on Windows.

I then launched the full stable-PTY stack with `--use-local-state`
`--confirm-local-state`, `QUESTLAB_LOCAL_STATE_ROOT` pointed at a disposable
WSL cache, and a separate disposable quest workspace. Preflight passed GREEN
with `-RequireIsolatedState` at revision 5. Pure CUA K&M (click/type/scroll and
observation only; no refresh or Playwright) verified the actual live projection:
an internal state-service objective moved The Hitman Resolve from 8/8 to 4/8
at revision 6, and a second verified objective moved revision 6 to 7, awarded
the service's own +30 XP/+15 coins, defeated The Hitman, unlocked The Bust Hound,
and created the Hitman Codex evidence. HUD, Journal, Codex, Character and
Homestead reflected those changes without refresh; shell and AI PTY labels
stayed `CONNECTED` throughout. The screenshot showed visible heart, coin and
flame SVG icons without nested pills.

The disposable runtime, tab, workspace and local cache were stopped/removed.
The protected canonical save remained revision 5 with SHA-256
`5618f9dd9ae2fc0724056ea08448e1736479772b59ada949bec08b5340fbd6f0`; no
canonical or Campaign `tutor.py` write occurred. The exact evidence is in
`GAME_STATE_SNAPSHOT_2026-09-16_0738.md`. A follow-up Claude Sonnet review was
attempted but the CLI reported its session limit until reset, so no new Claude
approval claim is made for this checkpoint.

### Isolated Dungeon/Practice savestate acceptance — 2026-09-16 10:14

The next bounded local slice was exercised in a disposable WSL cache and
workspace after the custody guard passed. Pure in-app-browser K&M (click,
scroll, typing and observation only; no Playwright) started an Infinite Dungeon
run, typed a code checkpoint, saved it, and submitted a state-service verdict
through the visible shell PTY. Revision `7 → 8` produced the service-owned
`+10` run score / `+5` run coins, a `DUNGEON ROOM CLEARED` notification, Floor 1
Room 2 and a blank editor buffer. The live Forge projection showed the new
question and retained both PTY connections.

Practice was opened separately. Its no-provider guard did not create a
session. A bounded gateway check then recorded a `Conditionals` / `multiple_choice`
Practice session and a provider-reviewed attempt at revisions `9` and `10`;
the rendered history showed `0 / 1 correct`, while the event returned
`reward_xp: 0` and `reward_coins: 0`. Campaign HUD, Dungeon score/currency and
the Campaign `tutor.py` boundary stayed unchanged. The UI displayed both
`PRACTICE DRILL READY` and `PRACTICE RESULT RECORDED` feedback cards.

After stopping and relaunching the runtime against the same disposable cache,
a fresh browser tab reopened the active run at Floor 1 / Room 2 with score 10,
5 run coins and a blank `dungeon.py` buffer. The backend log accepted both
`/ws/terminal/shell` and `/ws/terminal/ai` again. The normal launcher correctly
refused to treat the already-diverged disposable cache as a new migration
(`status: conflict`), so this restart proof used an explicit, already-approved
`QUESTLAB_STATE_PATH`; no merge or newest-revision choice was made.

Exact state, event and custody evidence is preserved in
`GAME_STATE_SNAPSHOT_2026-09-16_1014.md`. The protected canonical save stayed
revision 5 with SHA-256
`5618f9dd9ae2fc0724056ea08448e1736479772b59ada949bec08b5340fbd6f0`; the
disposable cache and runtime were removed afterward. This checkpoint closes
the local Dungeon/Practice projection proof; hosted persistence remains F-018.

## Codex/Homestead presentation checkpoint — 2026-09-16 10:44

The local UI polish pass stayed within the existing state-service contract.
Codex derives a compact evidence summary from the safe `codex_projection`
(indexed records, books with evidence, encounters, verified results and field
notes) and shows page-level encounter/question-pattern counts without exposing
future prompts or answer keys. Homestead now includes a live-loadout card for
campaign level/XP, canonical armor/trinket, coins and the source revision, so
the purchase balance is visibly tied to the same projection as the HUD.

The guarded Windows launcher was corrected to run the package as
`PYTHONPATH=. .venv/bin/python -m ide.quest`; direct script invocation from a
mounted checkout could not import `ide` during the custody preflight. Handoff
examples were updated accordingly. This did not change save custody, cloud
transport or terminal lifecycle.

Verification: WSL backend **78/78**, frontend **36/36**, Python compileall,
PowerShell preflight parse and Vite **1,345-module** production build all
passed. A disposable explicit-local-state browser run used only CUA
keyboard/mouse/scroll actions (no Playwright) and visibly showed Level 2,
50 XP, 55 coins, all five monochrome stat icons, the Codex evidence metrics,
the Homestead live-loadout card and `CONNECTED` shell/AI surfaces. The
disposable runtime/cache were removed; the protected canonical save,
legacy evidence and Campaign `tutor.py` were untouched.

### Claude Sonnet follow-up — 2026-09-16 10:50

The authenticated read-only review found no P0/P1 issue. It confirmed that the
new Codex/Homestead fields come only from the safe canonical projection, that
the React-owned HUD icon guard prevents DOM clobbering, and that the module
launcher command is valid. A pre-existing P2 fuzzy Codex fallback for records
without `page_id` was tightened to an exact/prefix concept match and covered by
a source assertion. Claude noted the frontend suite is source-regex based
rather than rendered-DOM based (known P3 boundary); it did not run commands or
touch the save, notebook, runtimes or PTYs.

## End-to-end bug hunt and hardening — 2026-09-16

The persistent bug ledger is [BUG_HUNT_LOG_2026-09-16.md](BUG_HUNT_LOG_2026-09-16.md).
The run used a disposable WSL workspace/cache on backend `7395` and frontend
`5215`, with pure in-app-browser keyboard/mouse/screenshot checks and no
Playwright. The protected repository save stayed revision 5 with SHA-256
`5618f9dd9ae2fc0724056ea08448e1736479772b59ada949bec08b5340fbd6f0`; the
root Campaign `tutor.py` remained untouched and untracked.

Two reviewer defects were repaired. Claude **Sonnet** found that prepending
the repository root to PTY `PATH` allowed editable files to shadow inherited
commands; both launchers now append the root and a regression test checks the
ordering. Copilot found that the PYR context GET path read a process-global
singleton across tabs; named contexts are now partitioned by `client_id`, with
coverage for independent tab-A/tab-B reads. Copilot also identified stale
Dungeon/Practice wording in this report; the Known Limitations now separates
the completed local slice from hosted/provider gates.

The patched runtime passed backend **79/79**, frontend **36/36**, Python
`compileall`, PowerShell preflight parsing and the Vite **1,345-module** build.
The live K&M pass showed the five monochrome HUD SVG icons, state-service
reward toasts, live HUD/Journal/Codex/Character updates, four cleared mobs and
the unlocked `The Bust Hound`, while both PTYs stayed `CONNECTED`. A visible
shell probe returned `CTX marker-A marker-B`, and a synthetic Level 99/999
coins workspace save left the HUD unchanged; the authority report marked the
workspace path non-authoritative. Copilot won the bug hunt with 5 weighted
points versus Claude Sonnet's 4; no new primary K&M defects were confirmed.

## Native Linux/CachyOS preflight checkpoint — 2026-09-16

To make the requested CachyOS laptop a first-class distribution target without
changing the state or cloud architecture, the branch now includes the
PowerShell-free read-only gate `tools/questlab-km-preflight.py`. It checks the
active branch/HEAD, backend and frontend proxy identity, one canonical state
authority, distinct legacy evidence, current revision and served SVG/loading
markers. `--require-isolated-state` refuses a mutating check against the
protected repository cache. The script performs no POST, state write,
Supabase call, process restart or PTY operation.

The onboarding guide documents a native CachyOS checkout, native `npm ci`, the
module-safe launcher and this preflight. The script's isolation checks and the
PowerShell-free contract are covered by the backend launcher tests. This is
tooling evidence only; F-058 still requires the actual CachyOS laptop's clean
install, browser K&M projection and connected shell/AI PTY proof before native
Linux support is marked verified.

Follow-up K&M on disposable ports `7415/5225` used the same native Linux
preflight at revisions 5 and 7. Forge, Character, Quest Journal, Codex,
Homestead, Campaign Tutor, Infinite Dungeon, Practice and Settings were
visited without a refresh. A visible state-service reward produced the
validated reward toast and live HUD/Character/Homestead updates; The Hitman
Journal projection and three Codex encounter books remained coherent. Both
PTY labels stayed `CONNECTED`, all five SVG icons remained visible and the
browser error/warning log was empty. The disposable runtime/cache/workspace
were removed afterward.

## Local two-device sync simulator checkpoint — 2026-09-16

`tools/questlab-local-sync-sim.py` now exercises the real local sync contract
without a cloud account or a second machine. It starts two temporary
`LocalStateService` caches from the canonical snapshot, applies validated
learning rewards on each side, pushes through a small in-memory CAS mailbox,
and verifies that both a stale mailbox push and an offline stale pull are
rejected with HTTP-style `409` conflict semantics. The scenario then chooses
**keep this device** explicitly,
imports through `sync_apply_cloud`, and checks that the two final projections
match. The source save digest is unchanged before/after and the temporary
device caches are removed automatically.

The direct CLI is module-safe and should be run with the checkout venv:
`.venv/bin/python tools/questlab-local-sync-sim.py --source progress.json`.
The simulator is deliberately bounded evidence, not proof of Supabase auth,
RLS, hosted mailbox transport, OneDrive custody or real two-device behavior.

## Current committed friend-bundle smoke — 2026-09-16

`tools/questlab-package.ps1` was run at pushed HEAD
`fdb4526a18177094e49a3aff69716c2d0b0f526b` with a disposable temp output.
The `QuestLab-fdb4526` directory and zip were created successfully. Its
packed `progress.json` matched the committed Git blob, the untracked Campaign
`tutor.py` was not present, and the generated `QUESTLAB_BUNDLE.txt` recorded
the committed-source-only boundary. The temp output was removed afterward.
This is source-custody evidence only; clean friend-machine and hosted sync
acceptance remain open.

## What can be completed without another device — 2026-09-16

The local implementation and verification surface is now exhausted for this
checkpoint. Without another machine, account-authorized hosted state, or a
native CachyOS session, work can continue safely in these bounded areas:

- deterministic state-service, sync-conflict, migration, mode-boundary and
  projection tests;
- disposable WSL/ext4 launch and browser K&M checks using an explicitly
  isolated cache, including reward/Resolve/Codex/Character/Homestead/Dungeon/
  Practice flows and PTY continuity;
- source-custody, launcher/preflight, dependency/build and committed-bundle
  checks; and
- issue-log, onboarding and release-readiness documentation.

The following claims cannot be made from this workstation alone: a real
PC-to-laptop cloud round-trip, authenticated Supabase/RLS acceptance, the
approved per-device save-custody migration, a clean friend Windows launch, a
native CachyOS certification, or a Tauri desktop proof. No cloud seed or
legacy-save edit was performed while recording this boundary. The public
activity-only tip merged during this checkpoint is `cab6b0c`.

## Post-merge regression and bundle verification — 2026-09-16

After the public activity fast-forward and the documentation checkpoint, the
full local gates were rerun against the unchanged implementation: WSL
backend **81/81**, frontend **36/36**, Python `compileall`, and the Windows
Vite build (**1,345 modules**) all passed. The cloud-free two-cache simulator
also passed; it rejected stale mailbox and stale local pulls with `409`,
performed an explicit keep-device `sync_apply_cloud`, and left the protected
save digest unchanged.

The committed-source packager was rerun at `f5e2a4119f9555e72d7b13d300bb91d00b91a773`.
The packed `progress.json` Git blob exactly matched `git rev-parse
HEAD:progress.json`, `tutor.py` was absent, the bundle manifest was present,
and the disposable output was removed. No new code, cloud state or player
file was written by this checkpoint; the latest browser K&M evidence therefore
remains the previously recorded isolated-cache run.

### F-050 sanitizer recheck — 2026-09-16

DOMPurify `3.4.15` was evaluated without changing the release dependency
graph. A temporary npm override made the audit report zero advisories, but
Monaco `0.56.0` loads its own bundled
`esm/vs/base/browser/dompurify/dompurify.js` at `3.4.8`; the override does not
replace that module. The override and lockfile change were reverted, the
working dependency tree was restored to the committed graph, and F-050 remains
open pending an upstream Monaco bundle with a patched embedded sanitizer. No
package workaround is being presented as a security fix.

## Clean ext4 live projection checkpoint — 2026-09-16

The current committed branch was cloned into the disposable WSL ext4 checkout
`/tmp/questlab-km-linux-repo-20260916-d`; the runtime used an isolated derived
cache and workspace on ports `7435/5245`. Native `npm ci`, the 1,345-module
Vite build, backend **81/81**, Python compilation and the Linux preflight all
passed before the browser check. The preflight confirmed the branch/HEAD,
distinct canonical and legacy paths, and `--require-isolated-state` custody.

Pure in-app-browser keyboard/mouse testing opened Forge, Character,
Homestead, Quest Journal and Codex. A visible Forge-shell call to the trusted
state service awarded `+35 XP / +20 Coins`; revision polling updated the HUD,
Character and Homestead without a refresh. Two visible trusted objective
mutations then cleared **The Empty Table**. The reward layer showed the
validated `+25 XP / +10 Coins`, `NEXT ENCOUNTER The Dealer's Hand`, and
`ACHIEVEMENT UNLOCKED First Blood`. Quest Journal moved to **The Dealer's
Hand (6/6 Resolve)** and Codex showed the defeated encounter with two verified
results and its evidence IDs. The five monochrome SVG HUD icons were visible
with no nested pills. Forge shell and AI terminal labels stayed `CONNECTED`,
and the browser error/warning log was empty.

The disposable runtime, browser tab, cache and workspace were stopped and
removed. The protected repository save and Campaign `tutor.py` were not
opened for writing. This is a local isolated-cache proof, not a second-device,
Supabase/RLS, cloud-mailbox or native CachyOS certification.

## Custody resume hardening — 2026-09-16

The disposable bug hunt found that an explicitly migrated per-device cache
could be advanced by the canonical state gateway but was then rejected as a
generic conflict on the next explicit local launch. That would strand a valid
Dungeon checkpoint after a normal Forge/runtime restart. The protected
repository `progress.json`, legacy/workspace save and root `tutor.py` were not
edited.

Commit `3def7a3` adds a gateway-written custody provenance marker containing
the reviewed source digest/revision and destination revision. A later local
launch reports `already-local` and resumes only when the source digest/revision
match and the destination is strictly advanced by the gateway. Unmarked,
malformed, changed-source or lower/equal-revision divergence still refuses;
there is no timestamp/newest-file merge and no second authoritative save.

Focused contract tests passed **21/21**; the full WSL backend suite passed
**84/84**, frontend **36/36**, Python compilation passed and Vite built **1,345
modules**. A disposable ext4 runtime relaunched through the guarded launcher,
restored the saved Dungeon Floor 1 / Room 1 checkpoint and code buffer, and
K&M inspection confirmed the HUD projection, Journal/Codex records and both
shell/AI PTY labels `CONNECTED`. No fresh external reviewer verdict was
available for this follow-up, so this is test-backed primary evidence rather
than a peer approval claim. Real F-039 migration approval and PC↔laptop
cloud/authenticated sync remain outside what this workstation can prove.

## PC stale-runtime diagnosis — 2026-09-16

The PC browser was still using the long-lived `5173 → 7332` Forge from
`~/projects/python-tutorial-DiddyDungeon` (F-025/F-031). The apparent current
frontend on `5174` was also pointed at backend `7333`, whose inherited
environment identified the old repository, so changing only the browser URL
would not have fixed the projection.

Without touching either existing process or PTY, a temporary current-tip
hybrid was launched: native Windows Vite on `5176` and the current WSL
`feature/cloud-sync-desktop` backend on `7335`. `/api/runtime` reported HEAD
`d7110b7`, canonical revision 5, the current repository path and the distinct
quest workspace; `/api/campaign` and in-app-browser K&M showed Level 2,
50/100 XP, 55 coins and The Hitman. The browser initially displayed the
explicit `SYNCING` state, then hydrated the canonical projection without a
refresh. The protected save digest stayed
`5618f9dd9ae2fc0724056ea08448e1736479772b59ada949bec08b5340fbd6f0`.

This is an operational stale-runtime correction, not a cloud-sync result.
The WSL OneDrive Rollup guard remains intentional; a permanent friend setup
should use the guarded launcher from a clean ext4/Linux dependency tree.

## Workspace source-transfer implementation — 2026-09-17

The missing-file behavior was a source-custody gap rather than a progression
sync failure: player state is intentionally owned by the Quest Lab state
service, while `blackjack.py`, Campaign `tutor.py` and `dungeon.py` remain
workspace files. The new `questlab-files` helper transfers those three files
through a dedicated `questlab-files/<project-branch>` Git ref and a sanitized
manifest. It does not push the workspace branch or any history, so
`progress.json`, session notes, `.env` files, caches and PTY state are never
included.

Push and pull are explicit. Push requires `PUSH_WORKSPACE_FILES`; pull first
returns a hash preview and requires `PULL_WORKSPACE_FILES` to write. A clean
checkout with an older tracked file may be updated. A dirty local allowlisted
file is a conflict and refuses by default; `--allow-overwrite` is a separate
opt-in that backs up the old file before an atomic replacement. Pull never
deletes a local file absent from the bundle. Paths, symlinks, UTF-8 text,
per-file size and SHA-256 values are validated on both sides.

The source, CLI wrapper, documentation and four focused tests are:

- `ide/workspace_transfer.py`
- `questlab-files`
- `WORKSPACE_TRANSFER.md`
- `ide/server/test_workspace_transfer.py`

The first source bundle was published from the reviewed WSL workspace on
2026-09-17 at `questlab-files/01-blackjack`, commit
`64696bee98228b342404525994122f69af4bbdaf`. Its manifest contains only the
three allowlisted files (748, 3396 and 0 bytes respectively); the local status
report confirms all three hashes match. The full WSL backend suite passed
**88/88** after this slice and Python compilation passed. No protected save,
legacy evidence, running PTY or Supabase state was changed. This local/Git
channel is deliberately separate from the still-unimplemented hosted source
artifact transport. A second device must still run the documented preview and
explicit pull; the transfer helper does not silently overwrite an open or
dirty workspace.

The first slice is intentionally disk/CLI based. A pull should be performed
after saving or closing an open Monaco buffer: the helper can protect dirty
on-disk Git files, but it cannot observe unsaved browser text and therefore
does not attempt a live editor hot-reload.

## Roadmap UI slice — 2026-09-17

This slice turns the existing Forge shell into a coherent local learning
surface without changing the canonical state authority or starting hosted
player-state transport. The default landing surface is now a Quest Hub, with
daily contracts, weekly goals, chapter progress and encounter silhouettes.
Locked chapters expose only their name/category and a generic locked summary;
future questions and answers remain hidden. A lightweight launch splash is
shown on first launch and after twenty minutes away, while the last view is
otherwise restored. The existing shell and AI WebSocket/PTY components remain
mounted while the splash or a non-editor view is visible.

Tutor Notebook and Practice now share one `tutor.py` editor surface. The
concept, question-lens and tier selectors are populated from the state-service
practice projection, and Ctrl+S/Ctrl+Enter/format shortcuts are captured before
Monaco can insert a newline. The AI prompt is explicitly bounded to teach,
practice and explain: it cannot invent Campaign/Dungeon rewards, reveal future
questions, or supply project-specific missing snippets. Transferable concept
notes use bounded `notes/<concept>.md` files through the notes API and the
workspace transfer helper; canonical field notes still go through the state
service.

Codex is presented as a larger field library with definitions, generic
examples, common mistakes, question lenses, verified encounter evidence and a
workspace notebook. Quest Journal uses paper-style pages with Previous/Next
controls. Homestead now shows the canonical live loadout/purse, a deterministic
shared daily cosmetic rotation and monochrome SVG item icons; the old injected
Future Loot/Trinket Vault and Weekly Raids blocks were removed from Homestead
and Journal. Weekly raid planning is represented on the Hub. Infinite Dungeon
now has a grid map of current/seen/rest/market/encounter rooms while its
question text stays state-issued and hidden until the room is entered.

The live acceptance test used only in-app-browser keyboard/mouse controls (no
Playwright) against a disposable isolated cache on the matching Forge/backend
pair. A valid Battle challenge/verdict reduced The Hitman from 8/8 to 4/8,
then a second validated verdict defeated it. Without a browser refresh the
polling projection showed:

- HUD 3 / 150 XP / 90 coins;
- a queued `OBJECTIVE VERIFIED` notification, then `MOB DEFEATED` (+30 XP,
  +15 coins) and `NEXT ENCOUNTER The Bust Hound`;
- Quest Journal Resolve 4/8, then 7/7 for the newly unlocked encounter;
- Character level/XP/coins and Homestead purse/revision updated;
- Codex entry for The Hitman with two attempts, both validated question
  lenses, two verified evidence IDs and mastery evidence 2;
- shell and AI PTY labels remained `CONNECTED` throughout.

The protected repository save was not mutated by this test (current SHA-256
`2FD91A49C8B8828E2AC1914275DBCCADA3733188B960AD375B068BD6AB91E0A1`). The
disposable state cache, frontend and backend should be stopped after review;
this is local revision-polling evidence, not a claim of second-device,
authenticated Supabase, native CachyOS or friend-machine certification.

Remaining gates are the real PC/laptop source-transfer round trip, hosted
account/avatar acceptance, native Linux packaging and the hosted Milestone C
campaign-projection migration/authenticated acceptance. The existing runtime
preflight may still report
`RUNTIME STALE` when a test intentionally uses the same checkout/workspace
path; that is a launcher/environment contract warning, not a second active
player-state authority.

## Dungeon route-selector slice — 2026-09-17

The Infinite Dungeon now uses the canonical state gateway for room selection.
`dungeon_start_run` and every resolved room return an active run to a selector
with three answer-free choices: Challenge room, Quiet rest and Wayfarer market.
`dungeon_choose_room` validates the run and choice ID, then issues only the
selected current room. React does not infer room types, future questions,
answers, score, damage or rewards. A verified encounter, completed rest or
left market creates the next selector and clears the `dungeon.py` projection;
the next question is not visible until a route is chosen.

The service, FastAPI route, selector UI, restart-safe projection and focused
tests are covered by the full WSL suite (**97/97**) and Vite build (**1,346
modules**). In-app-browser keyboard/mouse acceptance used a disposable cache:
the browser selected Challenge room, typed and checkpointed `answer = True`,
received a provider-validated verdict through the local bridge, and without a
refresh visibly returned to Room 2 with score/coins and the three route buttons.
It then selected Quiet rest, left the room, and visibly returned to the Room 3
selector. The backend was restarted while the browser stayed open; the same
Room 3 selector, score, run coins and blank-buffer checkpoint rehydrated, and
the shell terminal remained `CONNECTED`. The disposable cache was isolated;
the canonical root `progress.json`, active user Dungeon run, tutor notebook and
PTYs were not touched.

## Original redesign contract and 2026-09-17 regression repairs

The original product brief remains the reference for the local UI direction:
Hub-first launch with splash/last-route continuity, chapter silhouettes,
Codex field-library pages and concept notes, paper Journal pagination, current
loadout/shop presentation, state-owned Dungeon route selection and one shared
Tutor/Practice `tutor.py` IDE with concept/type/tier selectors. Practice keeps
independent no-reward history; it is not a second notebook and it cannot mutate
Campaign or Dungeon progression.

The isolated browser K&M hunt found and repaired three regressions against that
contract. Provider launch now records the tab-scoped provider handoff needed by
bounded Tutor/Practice requests. Legacy workspace `progress.json` is hidden
from the Forge file tree as well as rejected by generic file routes, so it
cannot look like a second live save. The bounded context bridge now permits a
read of the managed `tutor.py` for Tutor/Practice prompts while retaining the
generic-route write boundary. Focused tests and the full local gates are green;
details and scores are in `BUG_HUNT_LOG_2026-09-17.md` and issue IDs F-071–F-074.

## Native Linux launcher — 2026-09-17

The CachyOS target now has a guarded native-Linux entrypoint at
`tools/questlab-launch.sh`. It mirrors the Windows launcher's safety contract:
the intended branch and upstream are checked unless an explicit offline or
branch override is supplied, native `.venv/bin/python`, npm and frontend
dependencies are required, protected-save dirtiness is only warned, and the
workspace is passed explicitly to the module-safe `python -m ide.quest`
launcher. Backend reload is never enabled, so the shell and AI PTYs remain
stable during normal use. Local-custody migration remains an explicit opt-in
and still uses the state gateway's review/confirmation flow.

The wrapper passed Bash syntax/help checks, launcher contract tests (**14/14**)
and the full WSL backend suite (**98/98**). This removes the missing local
launcher/tooling gap (F-077) but does not certify a real CachyOS machine; the
F-058 kernel/package/install/K&M evidence gate remains open.

## Campaign evidence transport — 2026-09-17

The first cloud projection intentionally carried only player/equipment,
companion and Homestead fields. That was enough to move a level and purse but
not enough to move cleared mobs, project progress, Codex encounters, skills,
goals, achievements, Practice history or an active Dungeon editor checkpoint.
That omission explains the observed “HUD changed, Journal/Codex stayed
starter” behavior across devices.

The source-level repair extends the same allowlisted revision/CAS transport
with a bounded `campaign` domain. The local gateway strips local-only logs,
catalogues, profile data and arbitrary keys before validation. It carries
project/mob status and Resolve, Codex concepts/notes/validated results/mastery
evidence, streak/skills/achievements/goals, bounded Practice history, and the
answer-free current Dungeon run/loadout/room selector/editor checkpoint and
history. The browser SyncEngine projects the same shape for outbox, pull and
conflict paths.

The unapplied migration
`supabase/migrations/20260917000100_player_state_campaign_projection.sql`
updates the row-domain constraint and wraps the existing validator with a
campaign validator. Unknown nested fields, future reward/catalog data and
Dungeon answer-bearing fields are rejected. The current protected save
projects to **9,897 UTF-8 bytes**, below the 18,000-byte campaign allowance
and 24,000-byte total row bound.

Source-level verification is green: the full WSL backend suite **101/101**
(including state gateway **40/40**), migration contracts **7/7**, clean
disposable frontend **40/40**, Python compilation and the **1,346-module**
production build. The live OneDrive dependency tree still has the known F-033
missing `@supabase/supabase-js/package.json`; clean disposable frontend
tests/build remain the authoritative JS gate. No Supabase migration
was applied, no account was seeded, and no hosted or real PC↔laptop acceptance
claim is made. The protected save, root `tutor.py`, root `dungeon.py` and
existing shell/AI PTYs were untouched.

The read-only local two-device simulator now reports campaign continuity as
well as the player purse: the current protected snapshot retained **8
projects, 3 cleared mobs, 3 Codex encounters and the active Dungeon run/editor
checkpoint** on both disposable devices, while the source digest remained
unchanged. This is revision/CAS simulation evidence only, not authenticated
cloud proof.

### Codex note continuity recheck — 2026-09-17

The campaign allowlist now carries both canonical Codex `notes` and the
player-authored `player_notes` field through the Python gateway, browser
SyncEngine and hosted migration contract. A cloud apply preserves the note,
increments the local revision and records `sync_apply_cloud`; the merge also
retains local-only `learning_state.last_teachback` fields that are not part of
the cloud projection. Unknown fields and answer-bearing data remain rejected.

Verification after this repair: WSL backend **101/101**, migration contracts
**7/7**, clean disposable frontend **40/40**, Vite **1,346 modules**, and the
protected-save two-device simulator passed with an unchanged source digest.
No Supabase migration was applied, no hosted account was seeded, and no live
save or PTY was touched.

### Disposable account QA — 2026-09-17

For account-scoped testing, a separate disposable Supabase account was used
against isolated Forge runtimes. Profile/device registration and avatar
transport were verified: client B downloaded the avatar uploaded by client A,
and then picked up a replacement after the profile `updated_at` reference
changed. This validates the account-private portrait path without using the
user's account. Anonymous access to the portrait returned HTTP 400 and an
anonymous profile read returned HTTP 401, confirming the private RLS boundary.

The separate Git workspace-transfer check moved `blackjack.py`, `tutor.py`,
`dungeon.py`, and `notes/lists.md` between two temporary repositories. The
target `progress.json` and session notes were unchanged, and an unlisted
`notes/private.txt` was not transferred.

The first real authenticated campaign-sync attempt exposed a hosted
deployment gap: the live `save_player_state` RPC rejected the current source
projection with `next_state contains unsupported domains`, which means the
campaign-projection migration has not been applied to that Supabase project.
The source migration remains unapplied by design; no claim is made for real
PC↔laptop campaign sync until the hosted migration is approved/applied and
the two-device acceptance is repeated. The in-app browser could not attach a
fresh tab for this isolated run, so this account pass provides no new K&M
claim. No user save, user source file, or existing PTY was touched.

### Sync-status copy repair — 2026-09-17

The signed-in cache message was stale after campaign projection transport was
added: it still said Projects and Codex remained local. The message now names
Campaign, Journal and Codex as the surfaces sharing the state gateway, with a
regression test covering the emitted detail. Verification after the repair was
frontend **41/41** and a clean ext4 Vite build of **1,346 modules**; no user
save, notebook or PTY was touched.

### Hosted-schema failure UX — 2026-09-17

The hosted campaign validator's rejection was previously surfaced as a
generic cloud error. SyncEngine now reports `Cloud schema needs migration`,
names `20260917000100_player_state_campaign_projection.sql`, and keeps the
local outbox queued. A clean ext4 frontend run passed **42/42** with a
**1,346-module** build after the repair. This improves diagnostics only; it
does not bypass or apply the hosted migration.

### F-083 — signed-in first-frame status continuity

The account restore path briefly used a narrower “Campaign fields” status
before profile/device registration settled on the full Campaign, Journal and
Codex wording. That copy-only transition could look like sync instability even
though the PTY lifecycle and revision state were unchanged. Both states now use
the same description, with a regression guarding against the stale phrase.
Frontend verification remains **42/42** and the clean build transforms
**1,346 modules**.

### F-084 — native macOS friend onboarding

The friend guide now includes a native macOS path using Python, npm and the
existing guarded `tools/questlab-launch.sh`; it does not require WSL or a new
desktop runtime. The instructions preserve sibling-workspace separation,
gateway-owned state and stable PTYs. No Mac hardware was available for this
pass, so native install, live projection and PTY continuity remain explicitly
unverified.

### F-085 — account-scoped avatar cache repair

The disposable account test exposed a local-cache privacy edge that hosted RLS
could not prevent: signed-in uploads were also written to the unscoped local
avatar key. SyncEngine now writes signed-in fallbacks only under the account
identity, restores no unscoped portrait while signed in, and clears the visible
avatar when that account has no cloud portrait. Anonymous/offline uploads keep
the unscoped local behavior. Clean frontend verification passed **43/43** and
the production build transformed **1,346 modules**.

### F-086/F-087 — handoff precision

The handoff now makes two existing implementation boundaries explicit: the
public state envelope accepts only `player` and `pyr`, while `system` is
reserved for trusted in-process actions; and Campaign Tutor/Practice share one
managed `tutor.py`/notes surface while retaining separate Practice history and
no-reward progression boundaries. No runtime authority or file-write surface
was widened.

### F-088 — editor submit shortcut capture

The `Ctrl/Cmd+Shift+Enter` submit shortcut previously relied on a legacy
bubble-phase listener. Monaco could consume the event first when the editor had
focus, which made the shortcut appear to work only after clicking outside the
Python file. The React shell now intercepts the shortcut during capture, blocks
the editor insertion, and invokes the existing bounded `data-qol-submit` PYR
bridge. It does not grant the provider any new authority or change the PTY
lifecycle.

Verification: mounted source coverage **26/26**, clean ext4 frontend coverage
**44/44**, and a clean Vite production build. The protected save, root
`tutor.py`, root `dungeon.py`, and existing PTYs were not changed.

### Fresh Codex-owned QA identity recheck — 2026-09-17

A new mailbox-backed address was used for the requested disposable account
creation, but the configured Supabase Auth project returned HTTP **429**
`over_email_send_rate_limit` before creating a user/session. No service/admin
credential or bypass was used, and no password/token was retained. The prior
disposable account remains the valid hosted avatar evidence; local avatar,
workspace-transfer and revision/CAS sync checks remain green. A fresh hosted
account and authenticated UI round-trip must be retried after the provider
quota recovers.

### Handoff contract alignment — 2026-09-17

The older `FORGE_V2_HANDOFF.md` was stale relative to the current branch: it
said Practice could not use the managed `tutor.py`, called Dungeon/Practice
starter-only, and described verdict effects as display-only. It now matches the
implemented local contract while keeping provider authentication, hosted
campaign/Dungeon transport and real PC/laptop acceptance explicitly open.

### Sign-up quota feedback — 2026-09-17

The account-panel error path now converts Supabase's raw
`over_email_send_rate_limit` response into a bounded retry-later message that
explicitly confirms no account was created. The provider code is retained for
diagnostics without exposing its raw wording. Clean ext4 frontend coverage
passed **45/45** and the production build transformed **1,346 modules**.

### UI coherence and Dungeon inventory slice — 2026-09-17

This slice closes the next local Forge presentation gaps without widening the
state authority: Tutor is the single visible notebook destination, while the
separate Practice progression remains available through Tutor's selectors and
managed `tutor.py`. Hub is now a full-width destination with no rail or AI
column. Hidden AI stays mounted so the shell/AI PTYs are not recreated, but is
parked off-canvas and can be opened as a small pop-out from routes that hide
it. The Quest Journal's Main Quest page fills the available width, and Codex
now carries an Active Chapter panel beneath the Field Library.

Forge's active campaign-file sidebar now shows the state-service enemy Resolve
meter even before objectives are listed. Infinite Dungeon Run Loadout is a
bounded inventory menu backed by the canonical `dungeon_equip_item` mutation;
market gear is retained in the run checkpoint and can be re-equipped. The boot
splash now fades in/out and says `Welcome back, <username>` only after the
20-minute away threshold.

Verification after the changes: clean ext4 frontend **47/47**, mounted Forge
source coverage **28/28**, WSL backend suite **101/101**, and Vite production
build **1,346 modules**. The protected `progress.json` digest, `tutor.py`,
`dungeon.py`, shell PTY and AI PTY were left untouched. A fresh browser K&M
acceptance was not possible because the Codex in-app browser could not attach a
tab; this report makes no new live-browser claim.

### Character/Homestead and Battle workspace follow-up — 2026-09-17

Character and Homestead now use the same full-width presentation surface as the
Hub. The rail, context column, hidden IDE/terminal grid and normal AI column are
removed for those views; the AI component remains mounted off-canvas so a
manual pop-out does not recreate its PTY.

Quest Journal now has two in-journal screens: the paper Journal pages and a
dedicated Battle shell. Main Quest remains a readable chapter record with a
compact link into Battle; Resolve, objectives, boss validation and submission
live on the Battle screen. The Battle workspace uses a larger code-friendly
answer editor so learners can write implementation evidence or explanations in
the same focused manner as Forge/Tutor, while all rewards, Resolve and unlocks
still come only from validated state-service/provider results.

### React combat-surface ownership repair — 2026-09-17

The current Forge uses React for the Character, Homestead and Quest Journal
surfaces. The older `combatShell.js` compatibility observer was still appending
a legacy Battle Shell after every Journal render and rewriting the React
equipment list. That created duplicate Battle UI and visible jumps during the
one-second revision poll. The observer now removes stale legacy nodes only;
the React Battle screen and state-service projection remain the sole live
rendering path. This does not change canonical progression, cloud transport or
PTY lifecycle.

### Boss phase and trinket trigger slice — 2026-09-17

Boss requirements now persist as a bounded state-service mutation before the
final boss clear. The safe encounter projection exposes only verified phase
IDs, remaining phase IDs and a current phase label; provider prompts and answer
keys remain absent. The Battle screen renders that phase track and live event
notifications announce each validated phase. Three combat-only trinket effects
are state-owned: Ember Scythe adds one Impact to the first verified objective
of an encounter, Guardian Sigil negates one counterattack, and Phoenix Ember
revives at 1 HP once per encounter. Results/events include the trigger and
bounded effect values so React never recalculates them.

The allowlist and source-only Supabase migration carry the small boss-validation
record for the next approved hosted rollout; the migration was not applied to
the hosted project in this pass.

Verification for this slice: WSL backend discovery **103/103**, clean ext4
frontend tests **48/48**, and Vite production build (**1,346 modules**). The
protected save digest remained unchanged and the user PTYs were not restarted.

### Campaign equipment loadout projection — 2026-09-17

Homestead now has a real campaign loadout selector for Armor and Trinket. The
state service owns a small bounded catalogue and returns only the currently
equipped legacy value or IDs already recorded in `equipment.owned_armor` /
`equipment.owned_trinkets`; the browser never receives a future-loot list. A
player may equip an owned item through `POST /api/equipment/equip`, which writes
the canonical save and emits a revisioned `equip_equipment` event. Only trusted
game code can add ownership through `record_equipment_unlock`, with evidence and
reason fields retained in the event. The cloud projection allowlist carries the
bounded owned IDs for a future approved hosted migration; this pass did not
apply the hosted migration or infer any new rewards.

Verification: WSL backend discovery **105/105**, clean Windows-staging frontend
tests **49/49**, and Vite production build (**1,346 modules**). The protected
save, root `tutor.py`, root `dungeon.py`, shell PTY and AI PTY were untouched.
Fresh browser K&M remains unavailable because the Codex in-app browser could
not attach a tab.

### Wide-route navigation repair — 2026-09-17

Full-width presentation routes no longer strand the player. Hub, Character and
Homestead now render a compact `Wide route navigation` bar instead of relying
on the hidden activity rail. It routes through the existing React view state,
marks the active page, remains horizontally usable on small screens, and does
not recreate either PTY. The presentation surfaces stay full-width and the AI
remains parked unless explicitly opened.

Verification: frontend tests **49/49** and Vite production build (**1,346
modules**). Fresh browser K&M could not be attached in this environment.

### Navigation icon consistency repair — F-105

The persistent ActivityRail now uses the same inline monochrome SVG `RouteIcon`
set as the full-width Hub/Character/Homestead route bar. Legacy glyph/emoji
values were removed from the route metadata, and the rail's nested SVGs have
direct sizing/stroke rules so they cannot become nested stat-like pills. This
does not alter the canonical state authority, revision polling, cloud transport
or either PTY.

Verification: staged frontend tests **49/49** and Vite production build
(**1,346 modules**). Fresh browser K&M remains an environment gate.

### React navigation ownership repair — F-106

The React ActivityRail now declares its markup ownership explicitly. The legacy
`forgeEnhancements.js` icon bridge yields to that rail instead of replacing its
SVG children during MutationObserver passes, preventing a second writer from
competing with revision-driven React renders. The compatibility bridge remains
available for older non-React markup.

Verification: staged frontend tests **50/50**, WSL backend **105/105**, and
Vite production build (**1,346 modules**). No canonical save, cloud transport
or PTY lifecycle changed; fresh browser K&M remains unavailable in this
environment.

### Friend bundle protected-file repair — F-107

The guarded source packager now tolerates the normal learner checkout's
untracked `dungeon.py` and `notes/` alongside the already-protected local save
and `tutor.py`. It still refuses any committed-source edits and archives only
`git archive HEAD`, so protected workspace files cannot leak into a friend
bundle. The post-commit smoke produced `QuestLab-ed8db52` from `git archive
HEAD`, omitted `tutor.py`, `dungeon.py` and `notes/`, and proved the bundled
baseline `progress.json` matched the `HEAD` blob rather than the dirty local
cache.

### Wide-route callback compatibility repair — F-108

The alternate legacy Forge shell could render the wide Hub/Character/Homestead
route bar without passing the view-state callback into `GameScreen`. In that
shell the controls were visible but inert, which stranded a learner on
Homestead or Hub. The callback is now wired through `App.jsx`; the V2 shell was
already connected. The regression is covered by the frontend source test.

This repair only changes route navigation. It does not write campaign state,
touch the cloud transport, or recreate either PTY.

Post-publication verification: the current-source navigation suite passed
**32/32**, the clean ext4 frontend suite passed **51/51**, the WSL backend
suite passed **105/105**, and a fresh Vite production build transformed
**1,346 modules**. A fresh Codex browser tab could not attach, so this still
does not claim a new live click-through.

### Dungeon inventory cross-device repair — F-109

The local Dungeon checkpoint already persisted run-earned inventory, but the
browser campaign projection and the source-only hosted migration did not carry
that field. A second device could therefore restore the current room while
silently losing temporary run loot. The SyncEngine now projects a bounded
inventory list (`id`, `name`, `kind`, `armor`, `trinket`, `description`, max 24)
in both directions, and the migration validator accepts only that shape. A
two-device cloud round-trip regression proves the inventory survives a pull.

Verification: clean ext4 frontend tests **51/51**, Vite production build
**1,346 modules**, focused backend/migration tests **51/51**, and the full WSL
backend suite remains **105/105**. The hosted migration remains source-only
until the approved Milestone C application gate; no hosted sync claim is made.

### Wide-route navigation visibility hardening — F-110

The wide Hub, Character and Homestead surfaces retain a dedicated route bar,
but the strip now carries an explicit active-route marker and stays sticky above
the scrollable page with touch-sized targets. This keeps the player able to
reach Forge, Tutor, Journal, Codex, Character, Homestead, Dungeon and Settings
without restoring the side rail or remounting either PTY. The existing React
callback remains the only route state writer.

Verification: current-source Forge runtime suite **32/32**. No new live browser
click-through is claimed because the Codex browser tab could not attach.

### Quest Journal/Codex consolidation — F-111

Quest Journal is no longer a competing top-level route. The app normalizes any
legacy `quests` selection to `codex`, and the Codex Field Library now contains an
Active Quest sidebar with the current chapter, progress, cleared encounters and
silhouetted locked encounters. The sidebar is deliberately read-only: React
does not invent quest unlocks, rewards or hidden future answers.

Codex also owns a second journal-style tab, Battle Shell. Switching between
Books and Battle Shell remounts only the tab page for the visual page-turn
effect; it does not touch the shell or PTY keys. Battle Shell uses the existing
encounter projection and submit callbacks to show the current mob/boss story,
concept, status, objective count, question lens and validated Resolve/boss gate.
When a boss is available it renders the boss gate requirements instead of
showing the last defeated mob, while locked future content remains undisclosed.

Verification: current-source Forge runtime tests **32/32**; clean ext4 frontend
tests **51/51**; Vite production build transformed **1,346 modules**. Browser K&M
could not be performed because this Codex environment had no attachable tab, so
no new live click-through claim is made. The protected local `progress.json`,
`tutor.py` and `dungeon.py` files were not staged or edited, and the shell/AI PTY
keys remain outside the Codex tab state.

### Battle Shell encounter projection repair — F-112

During the final source review, the Battle Shell’s Question Lens expression was
found to reference `encounter` without receiving the canonical projection. The
component now accepts `encounter` explicitly, and both the compatibility Journal
call site and the visible Codex tab pass it through. This keeps the tab derived
from the same state-service data as Resolve, objective counts and boss phases;
it does not synthesize a question or reward in the browser.

The focused regression suite asserts the prop binding. Current-source tests
pass **32/32**, clean ext4 frontend tests pass **51/51**, and Vite transforms
**1,346 modules** successfully. Browser K&M is still an external gate because
the Codex environment has no attachable browser tab.

### Codex bounded reading workspace — F-113

The Codex presentation now behaves like a field-library workstation instead of
an infinite feed. The outer page keeps the compact hero and Books/Battle Shell
tabs visible. In Books, the Field Library/Active Quest index has its own
scrollable column and the selected concept page has its own reading column;
definition, examples, encounter evidence and notes stay together. Mastery
Signals are now part of that selected book pane instead of a second page-length
card below the library. At narrow widths the layout intentionally collapses to
one controlled column.

This is presentation-only: the canonical projection, revision/event source,
note gateway, reward authority and PTY keys are unchanged. Current-source tests
pass **32/32**, clean ext4 frontend tests pass **51/51**, and Vite transforms
**1,346 modules**. A local K&M attempt could not attach the Codex browser
webview, so visual click-through remains unclaimed.

### Stale Quest Journal command repair — F-114

The command palette no longer advertises a separate Quest Journal route. Codex
is the single navigation target for both the Field Library and Battle Shell;
the old icon name remains only in the legacy enhancement map for older markup
that may still be present during a compatibility transition.

Current-source Forge tests pass **32/32**. This was a navigation-only repair;
state authority, revision polling, PTY lifecycles and cloud transport were not
changed.

### Codex infinite-scroll cleanup — F-115

The first bounded Codex layout still exposed a permanent Mastery Signals tail,
which made the reading surface feel like the old infinite feed whenever a
player had several evidence records. The shell now uses explicit grid rows for
the compact hero, Books/Battle Shell tabs and the bounded workspace. The Field
Library index and selected book own their scroll independently with
`overscroll-behavior: contain`; the mastery grid is available from an
expandable section inside the selected book rather than growing the page by
default. Mobile intentionally switches to one controlled column.

The current-source Forge runtime suite passes **32/32**; a clean archive
frontend install passes **51/51** and Vite transforms **1,346 modules**. The
Windows working tree still has a locked esbuild binary, so the isolated archive
was used for dependency/build proof. No state, learner file, PTY or hosted
transport changed.

### Codex book-section overflow cleanup — F-116

The Codex no longer puts every learning surface into one long page. Each
selected concept book now has four small, explicit sections: Read for the
definition, examples, common mistakes and question lens; Encounters for the
validated mob evidence and results; Notes for the canonical/workspace
notebooks; and Mastery for recorded evidence and shields. The section switcher
keeps the book pane bounded and makes the useful content visible immediately.
No rewards, hidden answers or encounter facts are calculated in React.

The current-source Forge runtime suite passes **32/32**. Clean archive
frontend/build and browser K&M remain publication gates; no state, learner
file, PTY or hosted transport changed.

### Settings workspace-transfer bridge — F-117

Forge Settings now exposes the existing allowlisted `questlab-files` helper so
the learner can inspect the transfer ref, compare the four source-file groups,
preview incoming changes, publish reviewed project files and apply a pull only
after explicit confirmation. The API strips local absolute paths and reports
only whether a backup was created. A pull never touches `progress.json`, PTY
sessions or private logs, and the UI refreshes the file/tutor projections after
an apply while warning that open editor buffers should be reopened.

Focused WSL API tests pass **10/10** and current-source Forge tests pass
**32/32**. This is source transfer only; hosted player-state synchronization
and its approval/migration gates are unchanged.

### Compact Codex outer-scroll repair — F-118

The compact-width Codex fallback was still allowed to switch the whole screen
back to `height: auto` with visible outer overflow. That made a smaller Forge
window feel like the old infinite feed even though the desktop layout was
bounded. The fallback now keeps the Codex at the Forge viewport height,
stacks the index above the selected book, and limits scrolling to the index,
book and Battle Shell panes. No campaign projection, reward logic or PTY
lifecycle changed.

Current-source Forge tests pass **32/32**, including a regression that rejects
the old outer-scroll rule. Browser K&M remains an environment-gated visual
check because no Codex browser tab could attach.

### Account portrait projection repair — F-119

The portrait path now has one clear rendering owner. SyncEngine keeps the
validated account-scoped data URL in its in-memory view state, React renders it
on both the ActivityRail avatar and Character sheet, and the legacy enhancer
skips those marked nodes instead of replacing them during revision updates.
The existing private Storage path, account-scoped cache, anonymous local
fallback and remove behavior are unchanged.

Current-source Forge tests pass **32/32**. A real user-account PC/laptop
portrait round-trip is still an external hosted acceptance gate and is not
claimed here.
