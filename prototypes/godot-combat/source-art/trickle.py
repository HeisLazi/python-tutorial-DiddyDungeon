"""The daily trickle of hero-and-weapon redraws: which jobs are still to do.

A job is docs/review-art/whole/<skin>/<style>/<item>/ with a BRIEF.md. It is done when it has sheets and no REJECTED file.
`next N` prints up to N pending jobs (fewest attempts first, at most 3 attempts each), clears their old output and counts the attempt.
`status` prints the totals.

Usage:  python3 trickle.py next 4 | python3 trickle.py status
"""
import sys
from pathlib import Path

WHOLE = Path(__file__).resolve().parents[3] / "docs" / "review-art" / "whole"
MAX_ATTEMPTS = 3


def jobs():
    for brief in sorted(WHOLE.glob("*/*/*/BRIEF.md")):
        d = brief.parent
        if d.parts[-3] == "_ref":
            continue
        done = any(d.glob("*-sheet.png")) and not (d / "REJECTED").exists()
        attempts = int((d / "ATTEMPTS").read_text()) if (d / "ATTEMPTS").exists() else 0
        yield d, done, attempts


def main() -> None:
    all_jobs = list(jobs())
    if sys.argv[1] == "status":
        done = sum(1 for _, d, _ in all_jobs if d)
        spent = sum(1 for _, d, a in all_jobs if not d and a >= MAX_ATTEMPTS)
        print(f"{done} done, {len(all_jobs) - done - spent} pending, {spent} gave up after {MAX_ATTEMPTS} attempts, of {len(all_jobs)}")
        return
    pending = sorted(((a, str(d), d) for d, done, a in all_jobs if not done and a < MAX_ATTEMPTS))
    for attempts, _, d in pending[: int(sys.argv[2])]:
        for old in list(d.glob("*-sheet.png")) + [d / "preview.png", d / "REJECTED"]:
            old.unlink(missing_ok=True)
        (d / "ATTEMPTS").write_text(str(attempts + 1))
        print("/".join(d.parts[-3:]))


if __name__ == "__main__":
    main()
