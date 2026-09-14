# Forge QOL / Personalization Plan

## Implemented in current v2 branch

### Keyboard shortcuts

- `Ctrl+S` — save the active project file or Tutor Notebook.
- `Ctrl+Enter` — run the current Python file / `tutor.py`.
- `Ctrl+Shift+Enter` — submit the recent Forge terminal output to the currently launched AI terminal.
- `Shift+Alt+F` — Pretty / format.
- `Ctrl+\`` — focus the Forge terminal.
- `Ctrl+Shift+\`` — focus the AI terminal.

The Settings screen exposes the shortcut reference.

### Submit Run

The editor toolbar now gets a `Submit run` action.

Current v2 behaviour:

1. capture the most recent visible Forge terminal lines;
2. include the active filename;
3. attach a PYR reminder from the tutoring contract;
4. paste the context into the currently selected Codex / Claude / AGY terminal;
5. if synthetic paste is blocked by the browser, copy the context to the clipboard and focus the AI terminal instead.

This is intentionally a bridge toward the full PYR context system. The later controlled agent should receive terminal tail, active file, selection, git diff and quest state directly through explicit tools rather than DOM capture.

### Character portrait

The Character page supports a custom uploaded portrait.

Current v2 portrait storage is device-local browser state:

- PNG / JPEG / WebP accepted;
- input capped at 5 MB;
- image is center-cropped and resized to 256x256;
- saved as a compressed WebP data URL in localStorage;
- displayed in the Character sheet and activity-rail avatar.

Future option: promote the portrait to a portable profile asset stored by Quest Lab so it can move between devices/forks when the player wants that.

### Vector icon pass

RPG navigation and major HUD/game icons now use monochrome inline SVG marks instead of emoji glyphs. This keeps the Forge visual language closer to a game/IDE UI and avoids operating-system emoji styling differences.

---

# Next QOL work

## Command palette

Add a VS Code-like command palette, likely `Ctrl+Shift+P`, for:

- Run current file;
- Save;
- Pretty;
- Submit run;
- open Tutor Notebook;
- focus Forge terminal;
- focus AI terminal;
- switch Quest / Codex / Character / Homestead;
- launch Codex / Claude / AGY;
- reconnect terminals;
- reset layout.

## Better Submit Context

Move from visible-DOM terminal capture to explicit terminal-tail state managed by Quest Lab.

Submission packet should eventually include:

```text
active file path
selected code (optional)
recent terminal output
exit status / last command
current quest / mob / concept
learning phase
Reference Mode state
git diff summary
```

PYR should still be read-only on required project source and may write only `tutor.py` through controlled tools.

## Run history

Keep a short local list of recent runs:

```text
20:51 blackjack.py   exit 1
20:54 blackjack.py   exit 0
20:56 tutor.py       exit 0
```

Allow one-click Submit on any recent run.

## Portrait/Profile polish

- crop/position UI;
- optional border frames from Homestead cosmetics;
- portable profile image toggle;
- character banner/background cosmetics;
- later paper-doll/avatar mode for users who do not want a photo.

## Accessibility / layout

- keyboard navigation for activity rail;
- hide/show AI pane shortcut;
- hide/show terminal shortcut;
- Focus Mode;
- Tutor Mode preset;
- Battle Mode preset;
- per-panel minimum sizes remembered locally.
