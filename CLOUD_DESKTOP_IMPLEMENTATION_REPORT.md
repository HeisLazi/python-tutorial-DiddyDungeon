# Cloud/Desktop implementation report

Date: 2026-09-14
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
