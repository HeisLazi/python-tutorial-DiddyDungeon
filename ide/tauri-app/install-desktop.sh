#!/usr/bin/env bash
set -euo pipefail

# Build the Quest Lab desktop app and add it to the Linux app launcher.
# Run from the checkout you play from; the launcher entry points back at it.
# Low-RAM by design: two rustc jobs, no .deb/.rpm/.AppImage bundling.

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
src_tauri="$repo_root/ide/tauri-app/src-tauri"
bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
apps_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icon_dir="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"

command -v tauri >/dev/null || { echo "tauri CLI missing: npm install -g @tauri-apps/cli" >&2; exit 1; }
[[ -x "$repo_root/.venv/bin/python" ]] || echo "warning: $repo_root/.venv is missing; the app will fall back to python3" >&2

echo "Building Quest Lab (release, 2 jobs)…"
(cd "$src_tauri" && CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}" nice -n 10 tauri build --no-bundle)

mkdir -p "$bin_dir" "$apps_dir" "$icon_dir"
install -m 755 "$src_tauri/target/release/app" "$bin_dir/quest-lab"
install -m 644 "$src_tauri/icons/128x128@2x.png" "$icon_dir/quest-lab.png"

cat > "$apps_dir/quest-lab.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Quest Lab
GenericName=Python Quest Lab
Comment=Build games, learn to code, level up your character
Exec=env QUESTLAB_HOME=$repo_root $bin_dir/quest-lab
Icon=quest-lab
Terminal=false
Categories=Game;Education;Development;
StartupWMClass=app
EOF

command -v update-desktop-database >/dev/null && update-desktop-database "$apps_dir" >/dev/null 2>&1 || true
echo "Installed: $bin_dir/quest-lab  (launcher entry: Quest Lab → $repo_root)"
