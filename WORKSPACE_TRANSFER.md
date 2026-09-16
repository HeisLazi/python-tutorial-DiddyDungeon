# Quest Lab workspace file transfer

Quest Lab has two different kinds of data:

- Campaign progression (`progress.json`) is owned by the Quest Lab state
  service/cloud projection.
- Project source (`blackjack.py`, Campaign `tutor.py`, and `dungeon.py`) is
  owned by the player’s Git workspace.

The `questlab-files` helper transfers only the allowlisted source files through
a separate `questlab-files/<project-branch>` Git ref. It never pushes the
workspace branch wholesale, so local `progress.json`, session notes, secrets,
AI logs, caches, and PTY state cannot travel through this channel.

## Preview on either device

Run from the project workspace root. Resolve the root explicitly so a shell
started by Forge cannot accidentally select the platform checkout:

```bash
workspace_root="$(git rev-parse --show-toplevel)"
questlab-files --workspace "$workspace_root" --remote-branch 01-blackjack status
```

The report includes per-file SHA-256 values and separates allowlisted dirty
files from excluded changes. The command is read-only apart from Git’s normal
remote-ref fetch metadata.

## Send the current project files

On the device with the edits (for example, the laptop):

```bash
questlab-files --workspace "$workspace_root" --remote-branch 01-blackjack push \
  --confirm PUSH_WORKSPACE_FILES \
  --message "sync(workspace): send Blackjack learning files"
```

Push creates/advances `questlab-files/01-blackjack` with a sanitized tree. It
does not stage, commit, or alter the local Git index and it never includes
`progress.json`.

## Receive on the other device

Preview first:

```bash
questlab-files --workspace "$workspace_root" --remote-branch 01-blackjack pull
```

After reviewing the hashes, apply the allowlisted files explicitly:

```bash
questlab-files --workspace "$workspace_root" --remote-branch 01-blackjack pull \
  --confirm PULL_WORKSPACE_FILES
```

If a local allowlisted file differs, the pull stops without writing anything.
Only after reviewing the preview should you opt into replacement:

```bash
questlab-files --workspace "$workspace_root" --remote-branch 01-blackjack pull \
  --confirm PULL_WORKSPACE_FILES --allow-overwrite
```

Conflicting files are copied to a temporary backup directory before an atomic
replacement. A pull never deletes a local file that is absent from the bundle.
Afterward the received files remain ordinary working-tree files; commit them
on the project branch when you are satisfied.

Save/close the corresponding Monaco buffer before applying a pull. The helper
can see the workspace's on-disk Git state, but it cannot see unsaved browser
text; it deliberately does not hot-reload or overwrite an open editor buffer.
Launch Forge (or use its normal file reload) after the transfer has been
reviewed.

## Boundaries

- The transfer list is currently exactly `blackjack.py`, `tutor.py`, and
  `dungeon.py`.
- Campaign `tutor.py` remains a first-class Campaign notebook. Practice mode
  still cannot write it; this helper merely transfers the player-authored
  notebook between their own workspaces.
- Never use this helper for `progress.json`; use `questlab-state`/Forge for
  progression.
- The transfer ref has the same visibility as the configured Git remote. Review
  the three allowlisted files first and use a private repository when their
  contents should not be public.
- This is a local/Git transfer slice, not Supabase source-file transport. A
  hosted private artifact channel can be evaluated later if Git is not enough.
