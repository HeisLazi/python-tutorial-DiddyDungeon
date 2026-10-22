# Quest Lab desktop app

Quest Lab runs as a native window (Tauri) that starts and stops its own local
backend. No dev server, no browser tab.

## Launch

| How | What happens |
|---|---|
| **Diddy Dungeon** in your app launcher (Noctalia: Super+Space, search "diddy" or "quest lab") | Opens the app on your real save |
| `quest-lab` in a terminal | Same thing |
| `diddy-tauri` | Alias that runs `quest-lab` |
| `bash ./start-questlab.sh` | Old two-process dev mode (Vite + backend) in a browser. Don't run it at the same time as the app: both write the same `progress.json`. |
| `.venv/bin/python -m ide.quest --app` | Single-process app mode in your browser (prints the URL) |

## Install or update

From the checkout you play from:

```bash
bash ide/tauri-app/install-desktop.sh
```

This builds the release binary (2 rustc jobs, no installer bundles, so it is
gentle on RAM), installs it as `~/.local/bin/quest-lab`, and writes the
`Diddy Dungeon` launcher entry pointing at this checkout
(`~/.local/share/applications/quest-lab.desktop`).

You only need to re-run it when the Rust shell changes
(`ide/tauri-app/src-tauri`). Frontend and backend changes are picked up on
the next launch automatically.

## How it works

```
quest-lab (Tauri window)
  ├─ shows ide/tauri-app/splash/index.html while starting
  ├─ spawns: .venv/bin/python -m ide.quest --app --backend-port 7345
  │     ├─ rebuilds ide/frontend/dist if it is older than HEAD (~2s)
  │     └─ runs uvicorn ide.server.app_v2, which serves dist/ + /api + /ws
  ├─ waits for the "QUESTLAB_READY <url>" line, then navigates to it
  └─ on window close: SIGTERM to the launcher → uvicorn and PTYs shut down
```

- **Port 7345** is preferred (it falls forward if busy). It is separate from
  the browser launcher's 7331, so app settings (theme, active view) live in
  the app's own storage.
- **Wayland/Hyprland:** the app defaults to `GDK_BACKEND=x11` and
  `WEBKIT_DISABLE_COMPOSITING_MODE=1` for WebKitGTK unless you set them
  yourself.
- **Monaco** ships as prebuilt static files (`public/monaco`, copied by
  `scripts/copy-monaco.mjs`), so the frontend build takes ~2s and very little
  RAM, and every editor language (HTML, JS, SQL, Rust...) stays available.

## Troubleshooting

- **The splash says "Game over".** It shows the reason and the log path:
  `~/.local/state/QuestLab/desktop.log`.
- **Footer says FRONTEND STALE.** The code changed while the app was open.
  Close and reopen it; the UI rebuilds on launch.
- **Blank window on Wayland.** Try `WEBKIT_DISABLE_DMABUF_RENDERER=1 quest-lab`.
- **Not in the launcher.** Re-run `install-desktop.sh`; the entry is named
  "Diddy Dungeon".
