"""Create an independent starter save for a new desktop installation."""
from __future__ import annotations

import json
from pathlib import Path

from ide.server.state import LocalStateService, load_campaign_bounties


def fresh_progress() -> dict:
    stories = load_campaign_bounties()
    projects = []
    for branch, story in stories.items():
        if not isinstance(story, dict) or not isinstance(story.get("name"), str):
            continue
        projects.append({
            "branch": branch,
            "name": story["name"],
            "boss": story.get("boss", ""),
            "order": story.get("order", 999),
            "status": "available",
            "progress": 0,
            "mobs": [],
        })
    projects.sort(key=lambda item: (item["order"] if isinstance(item["order"], int) else 999, item["branch"]))
    first = next((p for p in projects if p["branch"] == "00-lantern-vale"), None)
    if first is None:
        raise RuntimeError("The starter campaign is missing from the installation")
    progress = {
        "meta": {"revision": 0},
        "player": {"level": 1, "xp": 0, "xp_next": 100, "lifetime_xp": 0, "coins": 0, "hp": 100, "max_hp": 100},
        "projects": projects,
    }
    LocalStateService._open_project(progress, first)
    if not first["mobs"]:
        raise RuntimeError("The starter campaign has no playable encounters")
    return progress


def initialize_new_save(path: Path) -> bool:
    """Create only when absent; never copy, replace or reset an existing save."""
    if not path.is_absolute():
        raise ValueError("The new save path must be absolute")
    if path.exists():
        return False
    # Prepare all content before creating the file; O_EXCL prevents a race
    # with another launcher from ever replacing its save.
    content = json.dumps(fresh_progress(), indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as target:
            target.write(content)
    except FileExistsError:
        return False
    return True
