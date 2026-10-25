"""The bridge to LearnHarness, the learner's own open-source study app.

The campaign is where the hunter fights; LearnHarness is home, where the
theory is studied. The bridge never writes LearnHarness data:

* its knowledge graph is read straight from its plain-file ledgers
  (``graph/nodes.jsonl``), so the game can show what was studied at home and
  let PYR build questions on it;
* the desktop app only answers its own window, so a study request becomes a
  handoff: the game opens LearnHarness and gives the learner a ready-made
  study brief to paste in as the session goal;
* a LearnHarness started from its repository (``npm run dev``) has an open
  local API; with ``LEARNHARNESS_URL`` set, the game creates the session and
  imports notes directly instead.

Nothing here reads LearnHarness credentials or chats.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

MAX_NODES = 5_000
MAX_LEDGER_BYTES = 20_000_000
STOPWORDS = frozenset(
    "the and for with that this from into your you are was were how what why when which their them they then than"
    " have has had not but can will its use using used make makes made each every more most also only just about"
    " python code program".split()
)


def data_dir() -> Path:
    configured = os.getenv("LEARNHARNESS_DATA_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".config" / "LearnHarness" / "data"


def notes_dir() -> Path:
    configured = os.getenv("LEARNHARNESS_NOTES_DIR")
    return Path(configured).expanduser() if configured else Path.home() / "Documents" / "DiddyDungeon notes"


def read_propositions(directory: Path | None = None) -> list[dict[str, Any]]:
    """Every idea in the knowledge graph, merged by id (the first line names
    it; later lines only add phrasings), tolerant of corrupt lines."""

    ledger = (directory or data_dir()) / "graph" / "nodes.jsonl"
    try:
        if not ledger.is_file() or ledger.stat().st_size > MAX_LEDGER_BYTES:
            return []
        lines = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    nodes: dict[str, dict[str, Any]] = {}
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if not isinstance(item, dict) or not all(isinstance(item.get(key), str) for key in ("id", "name", "statement")):
            continue
        aliases = [alias for alias in item.get("aliases", []) if isinstance(alias, str)] if isinstance(item.get("aliases"), list) else []
        known = nodes.get(item["id"])
        if known is None:
            if len(nodes) >= MAX_NODES:
                continue
            nodes[item["id"]] = {"id": item["id"], "name": item["name"][:200], "statement": item["statement"][:600], "aliases": aliases[:12]}
        else:
            known["aliases"] = list(dict.fromkeys([*known["aliases"], *aliases]))[:12]
    return list(nodes.values())


def _terms(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z][a-z0-9_]{2,}", text.lower()) if word not in STOPWORDS}


def related(propositions: list[dict[str, Any]], text: str, limit: int = 6) -> list[dict[str, Any]]:
    """The studied ideas that share the most words with ``text``."""

    wanted = _terms(text)
    if not wanted:
        return []
    scored = []
    for node in propositions:
        haystack = _terms(" ".join([node["name"], node["name"], node["statement"], *node["aliases"]]))
        score = len(wanted & haystack)
        if score:
            scored.append((score, node["name"], node))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [node for _score, _name, node in scored[:limit]]


def is_running() -> bool:
    """Whether the LearnHarness desktop app is open (by process name only)."""

    proc = Path("/proc")
    if not proc.is_dir():
        return False
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            first = (entry / "cmdline").read_bytes().split(b"\0", 1)[0].decode("utf-8", "replace")
        except OSError:
            continue
        if Path(first).name.lower() == "learnharness" or first.lower().endswith("learnharness.appimage"):
            return True
    return False


def _launcher() -> list[str] | None:
    app = os.getenv("LEARNHARNESS_APP")
    if app and Path(app).expanduser().is_file():
        return [str(Path(app).expanduser())]
    desktop = Path.home() / ".local" / "share" / "applications" / "learnharness.desktop"
    if desktop.is_file() and shutil.which("gtk-launch"):
        return ["gtk-launch", "learnharness"]
    image = Path.home() / "Applications" / "LearnHarness.AppImage"
    if image.is_file():
        return [str(image)]
    return None


def installed() -> bool:
    return _launcher() is not None or data_dir().is_dir()


def launch() -> bool:
    """Open LearnHarness if it is not already open. True when it is open or opening."""

    if is_running():
        return True
    command = _launcher()
    if not command:
        return False
    try:
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return False
    return True


_API_CACHE: dict[str, Any] = {"url": None, "ok": False, "at": 0.0}


def api_url() -> str | None:
    """A LearnHarness API the game may call: only an explicitly configured
    one (``LEARNHARNESS_URL``) that answers without a desktop guard."""

    url = (os.getenv("LEARNHARNESS_URL") or "").strip().rstrip("/")
    if not re.match(r"^http://(127\.0\.0\.1|localhost)(:\d+)?$", url):
        return None
    if _API_CACHE["url"] == url and time.monotonic() - _API_CACHE["at"] < 30:
        return url if _API_CACHE["ok"] else None
    try:
        with urllib.request.urlopen(f"{url}/api/chats", timeout=2) as response:
            ok = response.status == 200 and isinstance(json.loads(response.read(200_000)).get("chats"), list)
    except (OSError, ValueError, urllib.error.URLError):
        ok = False
    _API_CACHE.update(url=url, ok=ok, at=time.monotonic())
    return url if ok else None


def study_brief(topic: str, context: str, ideas: list[dict[str, Any]]) -> str:
    lines = [f"I want to really understand {topic}.", f"Why: in DiddyDungeon I am {context}."]
    if ideas:
        lines.append("Ideas I have already studied that may connect:")
        lines.extend(f"- {node['name']}: {node['statement']}" for node in ideas)
    lines.append("Teach me from what I already know, then check I can apply it to my own code.")
    return "\n".join(lines)


def create_session(url: str, title: str, ideas: list[dict[str, Any]]) -> dict[str, Any]:
    body = {"title": title, "graphContext": {"propositions": [{"id": node["id"], "name": node["name"], "statement": node["statement"]} for node in ideas]}}
    request = urllib.request.Request(f"{url}/api/chats", data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read(200_000))


def import_notes(url: str, filename: str, text: str) -> dict[str, Any]:
    boundary = f"----questlab{uuid.uuid4().hex}"
    payload = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{filename}\"\r\nContent-Type: text/markdown\r\n\r\n"
    ).encode("utf-8") + text.encode("utf-8") + f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = urllib.request.Request(f"{url}/api/graph/import", data=payload, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read(1_000_000))


def notes_markdown(progress: dict[str, Any], contracts: dict[str, Any]) -> tuple[str, str]:
    """The learner's own notes and cleared work on the active campaign, as a
    Markdown file name and text for LearnHarness to import."""

    project = next((item for item in progress.get("projects", []) if isinstance(item, dict) and item.get("status") == "active"), {})
    name = str(project.get("name") or project.get("branch") or "campaign")
    lines = [f"# DiddyDungeon notes: {name}", ""]
    for mob in project.get("mobs", []) if isinstance(project.get("mobs"), list) else []:
        if not isinstance(mob, dict) or mob.get("status") not in {"defeated", "cleared"}:
            continue
        contract = contracts.get(mob.get("name")) or {}
        lines.append(f"## {mob.get('name')} ({mob.get('concept') or contract.get('concept') or ''})")
        for objective in contract.get("objectives", []) if isinstance(contract.get("objectives"), list) else []:
            if isinstance(objective, dict):
                lines.append(f"- {objective.get('label')}: {objective.get('brief')}")
        lines.append("")
    codex = progress.get("codex") if isinstance(progress.get("codex"), dict) else {}
    notes = []
    for entry in codex.get("encounters", []) if isinstance(codex.get("encounters"), list) else []:
        if not isinstance(entry, dict):
            continue
        for note in entry.get("player_notes", []) if isinstance(entry.get("player_notes"), list) else []:
            text = note.get("text") if isinstance(note, dict) else note
            if isinstance(text, str) and text.strip():
                notes.append(f"- {entry.get('mob_name')}: {text.strip()}")
    if notes:
        lines += ["## My notes", *notes, ""]
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "campaign"
    return f"diddydungeon-{slug}.md", "\n".join(lines).strip() + "\n"
