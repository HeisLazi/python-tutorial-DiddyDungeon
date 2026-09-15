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
- `SyncEngine` now owns all player-state Supabase reads/writes. It syncs only
  player progression/HP, armor/trinket/title, companion state and Homestead
  ownership/equipped cosmetics. Projects, Codex/encounter history,
  skills/mastery evidence, activity and cosmetic catalog/purchase history
  remain local in this first transport slice and are preserved by cloud pulls.
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
- A real browser-level PYR verdict path is still pending; the current context
  bridge/verdict boundary has no provider-side answer adjudicator or player
  Battle UI yet. Do not treat a caller-supplied verdict as proof of learning.
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
