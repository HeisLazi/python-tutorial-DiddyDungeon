# Local state-custody migration plan

This plan was produced from the 2026-09-15 Claude read-only review and the
current Quest Lab handoff. It is deliberately an approval-gated Slice 7
follow-up. It does not move, overwrite, or reconcile the player's current
`progress.json`.

## Why this is the next gate

The state service already prevents the quest workspace's `progress.json` from
becoming a second live save. The remaining local risk is that the tracked
platform `progress.json` is also replicated by OneDrive and can be affected by
checkout operations. A per-device cache would remove that third-writer risk,
but it must not silently strand the player's current progress or pretend to
provide cross-device sync before hosted transport is accepted.

## Proposed custody contract

1. The state service computes an opaque checkout namespace from the platform
   and workspace roots. The namespace is safe for a per-device directory name;
   raw paths are never sent to cloud/device metadata.
2. The default launcher remains unchanged until the player explicitly approves
   migration. A preview report exposes the current path, proposed path,
   migration status and the fact that approval is required.
3. An explicit migration command runs through the local state gateway. It reads
   the canonical snapshot under the shared lock, validates its schema/revision,
   and copies it atomically to the proposed per-device path. It never merges a
   legacy workspace save and never deletes the source.
4. Migration is copy-once and idempotent. A marker records the source identity,
   source revision and destination identity. A later launch never overwrites a
   non-empty destination; if source and destination disagree, the service
   reports a conflict and stops for human choice.
5. Only an explicit launcher opt-in switches `QUESTLAB_STATE_PATH` to the
   approved destination for that launch. Later default launches remain on the
   tracked cache until the player separately chooses custody; the old tracked
   file stays read-only legacy evidence until archival is approved.
6. With no Supabase configuration, each device remains local-only. This plan
   does not claim cross-device progress transport; the existing cloud-sync
   engine and provider-authentication gates remain unchanged.

## Implementation slices

### A. Preview and contract

- Add a read-only custody projection to `/api/runtime`, `/api/state/revision`
  and `questlab-state runtime`.
- Include `mode`, `canonical_path`, `proposed_path` (when configured),
  `migration_status`, `source_revision`, and `approval_required`.
- Add tests for opaque namespace stability, path containment, missing source,
  existing destination, and conflicting revisions.

### B. Gateway migration command

- Implemented behind `POST /api/state/custody/migrate` and
  `questlab-state custody-migrate`; there is no arbitrary path input. The
  server derives the destination from its configured local-state root and
  opaque namespace.
- The operation requires the reviewed source revision and the explicit
  `MIGRATE_LOCAL_STATE` confirmation token.
- It writes a temporary file beside the destination, fsyncs/replaces it
  atomically, then writes a bounded marker. No campaign reward/event is
  invented and the campaign revision remains unchanged because the snapshot
  contents are copied without mutation.
- It refuses workspace/legacy paths, symlink destinations, non-empty
  divergent destinations, and any source revision race. Identical retries
  return `already-local` and never overwrite the destination.

### C. Opt-in launcher and onboarding

- Implemented: `-MigrateLocalState`/`--use-local-state` prints the preview,
  requires the player to type `MIGRATE_LOCAL_STATE` (or use the explicit
  non-interactive confirmation flag), then switches `QUESTLAB_STATE_PATH` for
  that launch only. The default launch remains tracked-cache mode.
- The wrapper refuses non-interactive migration without confirmation and does
  not start either child process when review/confirmation is missing.
- Document that this is local custody only; cloud sync, two-device mailbox
  transport, and hosted Dungeon state remain separate acceptance gates.

### D. Clean two-device-equivalent proof

- Extract two clean ext4 archives with separate disposable state roots and run
  `npm ci` plus the production build in each.
- Launch both with no `VITE_SUPABASE_*` variables. Confirm independent opaque
  namespaces, independent local revisions, and no workspace `progress.json`
  writes.
- Use browser click/scroll/type K&M checks on each Forge: canonical HUD,
  Journal/Codex projections, SVG icons, and shell/AI `CONNECTED` markers.
- Use a typed state-service mutation in one disposable device and prove the
  other stays unchanged. This proves isolation, not hosted sync.

## Required gates before enabling the default

- Player explicitly approves the custody migration for the real save.
- Gateway preview and copy-once migration tests are green.
- Full WSL backend/frontend suites and Windows Vite build are green.
- Two isolated clean-install K&M runs pass with no browser refresh and no PTY
  reset.
- The issue log records the exact source/destination/revision evidence.
- F-001/F-009/F-010 remain open until provider-authenticated adjudication and
  tab/account challenge isolation are proven; no Supabase seed is part of this
  local custody gate.
