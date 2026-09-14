#!/usr/bin/env python3
"""Build activity.json from GitHub commit history and refresh README activity stats.

Uses only the Python standard library so it can run inside GitHub Actions.
The resulting activity score rewards consistency and caps raw commit spam.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "activity_config.json"
ACTIVITY_PATH = ROOT / "activity.json"
README_PATH = ROOT / "README.md"
START_MARKER = "<!-- ACTIVITY_STATS_START -->"
END_MARKER = "<!-- ACTIVITY_STATS_END -->"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def github_get(url: str, token: str | None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "python-quest-lab-activity-sync",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def local_day(dt: datetime, offset_hours: int):
    return (dt.astimezone(timezone.utc) + timedelta(hours=offset_hours)).date()


def calc_current_streak(active_days: set, today):
    if not active_days:
        return 0
    cursor = today
    if cursor not in active_days:
        yesterday = today - timedelta(days=1)
        if yesterday not in active_days:
            return 0
        cursor = yesterday
    streak = 0
    while cursor in active_days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def calc_longest_streak(active_days: set):
    if not active_days:
        return 0
    longest = 1
    current = 1
    ordered = sorted(active_days)
    for previous, day in zip(ordered, ordered[1:]):
        if day == previous + timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def update_readme(activity: dict):
    if not README_PATH.exists():
        return
    text = README_PATH.read_text(encoding="utf-8")
    block = f"""{START_MARKER}

| Dev activity | Current |
|---|---:|
| Activity score | **{activity['activity_score']}** |
| Commit streak | **{activity['current_streak']} days** — best: {activity['longest_streak']} |
| Commits | **{activity['commits_7d']}** / 7d · **{activity['commits_30d']}** / 30d |
| Active dev days | **{activity['active_days_7d']}** / 7d · **{activity['active_days_30d']}** / 30d |
| Active branches (30d) | **{activity['active_branches_30d']}** |
| Last commit day | **{activity['last_active_day'] or 'none yet'}** |

`Activity score` is machine-derived from commit history. It rewards active days and streaks, caps effective commits per day, and does **not** grant learning XP or Mastery Shields.

{END_MARKER}"""
    if START_MARKER in text and END_MARKER in text:
        before = text.split(START_MARKER, 1)[0]
        after = text.split(END_MARKER, 1)[1]
        text = before + block + after
    else:
        text += "\n\n## Dev Activity League\n\n" + block + "\n"
    README_PATH.write_text(text, encoding="utf-8")


def main():
    config = load_json(CONFIG_PATH)
    repo = os.getenv("GITHUB_REPOSITORY", "HeisLazi/python-tutorial-DiddyDungeon")
    token = os.getenv("GITHUB_TOKEN")
    player_login = os.getenv("ACTIVITY_PLAYER_LOGIN", config.get("player_login", repo.split("/", 1)[0]))
    offset_hours = int(config.get("utc_offset_hours", 0))
    history_days = int(config.get("history_days", 120))
    cap_per_day = int(config.get("commit_cap_per_day", 5))
    ignored_prefixes = tuple(config.get("ignored_commit_prefixes", []))
    score_cfg = config.get("activity_score", {})

    now_utc = datetime.now(timezone.utc)
    now_local_day = local_day(now_utc, offset_hours)
    cutoff_dt = now_utc - timedelta(days=history_days)

    started_raw = config.get("competition_started_at")
    competition_started = parse_dt(started_raw).astimezone(timezone.utc) if started_raw else None
    if competition_started and competition_started > cutoff_dt:
        cutoff_dt = competition_started

    api = f"https://api.github.com/repos/{repo}"
    repo_meta = github_get(api, token)
    default_branch = repo_meta.get("default_branch", "main")
    branches = github_get(f"{api}/branches?per_page=100", token)

    unique = {}
    branch_shas = defaultdict(set)

    for branch in branches:
        branch_name = branch["name"]
        encoded = urllib.parse.quote(branch_name, safe="")
        for page in range(1, 6):
            commits = github_get(f"{api}/commits?sha={encoded}&per_page=100&page={page}", token)
            if not commits:
                break
            should_stop = False
            for item in commits:
                commit = item.get("commit", {})
                message = (commit.get("message") or "").splitlines()[0]
                if ignored_prefixes and message.startswith(ignored_prefixes):
                    continue

                linked_author = item.get("author")
                if linked_author and linked_author.get("login"):
                    if linked_author["login"].lower() != player_login.lower():
                        continue

                stamp = commit.get("author", {}).get("date") or commit.get("committer", {}).get("date")
                if not stamp:
                    continue
                dt = parse_dt(stamp).astimezone(timezone.utc)
                if dt < cutoff_dt:
                    should_stop = True
                    continue

                sha = item["sha"]
                unique[sha] = {"sha": sha, "date": dt, "message": message}
                branch_shas[branch_name].add(sha)

            if should_stop or len(commits) < 100:
                break

    by_day = Counter()
    cutoff_7 = now_local_day - timedelta(days=6)
    cutoff_30 = now_local_day - timedelta(days=29)

    for item in unique.values():
        by_day[local_day(item["date"], offset_hours)] += 1

    # Shared history exists on many project branches. Count main normally, then
    # count only commits that are not already reachable from main for each
    # non-default branch. This makes the branch breakdown represent actual
    # branch-specific work rather than duplicated ancestry.
    default_shas = branch_shas.get(default_branch, set())
    branch_counts_30 = Counter()
    for branch_name, shas in branch_shas.items():
        candidates = shas if branch_name == default_branch else shas - default_shas
        count = 0
        for sha in candidates:
            item = unique.get(sha)
            if item and local_day(item["date"], offset_hours) >= cutoff_30:
                count += 1
        if count:
            branch_counts_30[branch_name] = count

    active_days = set(by_day)
    current_streak = calc_current_streak(active_days, now_local_day)
    longest_streak = calc_longest_streak(active_days)
    commits_7 = sum(count for day, count in by_day.items() if day >= cutoff_7)
    commits_30 = sum(count for day, count in by_day.items() if day >= cutoff_30)
    active_days_7 = sum(1 for day in active_days if day >= cutoff_7)
    active_days_30 = sum(1 for day in active_days if day >= cutoff_30)
    active_branches_30 = len(branch_counts_30)

    effective_commits_30 = sum(
        min(by_day.get(cutoff_30 + timedelta(days=i), 0), cap_per_day)
        for i in range(30)
    )
    branch_bonus_count = min(active_branches_30, int(score_cfg.get("max_branch_bonus", 8)))
    activity_score = (
        active_days_30 * int(score_cfg.get("active_day_points", 12))
        + effective_commits_30 * int(score_cfg.get("effective_commit_points", 2))
        + current_streak * int(score_cfg.get("current_streak_points", 8))
        + branch_bonus_count * int(score_cfg.get("active_branch_points", 5))
    )

    daily_30 = []
    for i in range(30):
        day = cutoff_30 + timedelta(days=i)
        daily_30.append({"date": day.isoformat(), "commits": by_day.get(day, 0)})

    most_active = None
    if commits_30:
        day, count = max(
            ((day, count) for day, count in by_day.items() if day >= cutoff_30),
            key=lambda x: (x[1], x[0]),
        )
        most_active = {"date": day.isoformat(), "commits": count}

    branch_activity = [
        {"branch": branch, "commits": count}
        for branch, count in branch_counts_30.most_common()
    ]

    activity = {
        "schema_version": 1,
        "generated_at": now_utc.isoformat(),
        "source": "github-commit-history",
        "repository": repo,
        "player_login": player_login,
        "competition_started_at": started_raw,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "commits_7d": commits_7,
        "commits_30d": commits_30,
        "active_days_7d": active_days_7,
        "active_days_30d": active_days_30,
        "active_branches_30d": active_branches_30,
        "activity_score": activity_score,
        "effective_commits_30d": effective_commits_30,
        "total_unique_commits_scanned": len(unique),
        "last_active_day": max(active_days).isoformat() if active_days else None,
        "most_active_day_30d": most_active,
        "daily_30d": daily_30,
        "branch_activity_30d": branch_activity,
    }

    ACTIVITY_PATH.write_text(json.dumps(activity, indent=2) + "\n", encoding="utf-8")
    update_readme(activity)
    print(json.dumps({k: activity[k] for k in ["activity_score", "commits_7d", "commits_30d", "active_days_30d", "current_streak"]}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"activity sync failed: {exc}", file=sys.stderr)
        raise
