#!/bin/sh
# Rebuild the checked-in, single-threaded Godot combat web export.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
mkdir -p "$ROOT/ide/frontend/public/combat"
godot --headless --path "$ROOT/prototypes/godot-combat" --import
godot --headless --path "$ROOT/prototypes/godot-combat" --export-release Web ../../ide/frontend/public/combat/index.html
# Godot's generated template includes whitespace-only lines; normalize them
# so the checked-in export passes the repository's whitespace check.
python3 - "$ROOT/ide/frontend/public/combat/index.html" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()).rstrip() + '\n')
PY
