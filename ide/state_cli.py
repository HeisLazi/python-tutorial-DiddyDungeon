"""Small localhost-only bridge for named Quest Lab state commands.

Usage examples::

    python -m ide.state_cli learning-event --kind teachback \
      --evidence-id session-001 --reason "Explained list indexing"
    python -m ide.state_cli homestead-purchase --item-id cursor-golden-spark

System/game actions such as HP changes, rewards and achievements intentionally
remain in-process only; the raw AI terminal cannot use this helper to grant
progression.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.client import HTTPException as ClientHTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ide.server.security import DEFAULT_FRONTEND_PORT
from ide.server.state import CUSTODY_CONFIRMATION_TOKEN, MAX_IDENTIFIER_LENGTH, MAX_REASON_LENGTH


def _port(value: str) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def _bounded_text(value: str, field: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum or any(ord(character) < 32 for character in normalized):
        raise argparse.ArgumentTypeError(f"{field} must be bounded text without control characters")
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply a named Quest Lab state command through localhost Forge.")
    parser.add_argument(
        "--backend-port",
        type=_port,
        default=_port(os.getenv("QUESTLAB_BACKEND_PORT", "7331")),
        help="local Forge backend port (default: QUESTLAB_BACKEND_PORT or 7331)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    learning = subparsers.add_parser("learning-event", help="record a bounded PYR learning-evidence event")
    learning.add_argument("--kind", choices=("teachback", "practice", "forge", "review", "interview", "mob", "bugfix", "session"), required=True)
    learning.add_argument("--evidence-id", required=True)
    learning.add_argument("--reason", required=True)

    reference = subparsers.add_parser("reference-mode", help="record a non-reversible Reference Mode assist event")
    reference.add_argument("--milestone-id", required=True)
    reference.add_argument("--evidence-id", required=True)
    reference.add_argument("--reason", required=True)
    reference.add_argument("--xp-forfeited", type=int, default=0)

    purchase = subparsers.add_parser("homestead-purchase", help="purchase a player cosmetic")
    purchase.add_argument("--item-id", required=True)

    equip = subparsers.add_parser("homestead-equip", help="equip an owned player cosmetic")
    equip.add_argument("--item-id", required=True)

    hp = subparsers.add_parser("hp-change", help="reserved system/game command")
    hp.add_argument("--amount", type=int, required=True)
    hp.add_argument("--reason", required=True)
    hp.add_argument("--encounter-id", required=True)

    achievement = subparsers.add_parser("achievement", help="reserved system/game command")
    achievement.add_argument("--achievement-id", required=True)
    achievement.add_argument("--evidence-id", required=True)
    achievement.add_argument("--reason", required=True)
    subparsers.add_parser("legacy-report", help="compare canonical state with a non-authoritative workspace progress.json")
    subparsers.add_parser("authority", help="show the canonical state authority and current revision")
    subparsers.add_parser("campaign", help="read the current canonical campaign projection")
    subparsers.add_parser("runtime", help="read checkout, path and command health for the running Forge")
    subparsers.add_parser("custody", help="preview the opt-in per-device state custody destination")
    custody_migrate = subparsers.add_parser(
        "custody-migrate",
        help="copy the reviewed canonical snapshot to the derived per-device cache",
    )
    custody_migrate.add_argument("--expected-revision", type=int, required=True)
    custody_migrate.add_argument(
        "--confirm",
        choices=(CUSTODY_CONFIRMATION_TOKEN,),
        required=True,
        help=f"explicit confirmation token: {CUSTODY_CONFIRMATION_TOKEN}",
    )
    return parser


def _reserved(command: str) -> int:
    print(
        f"{command} is reserved for trusted in-process game code; no gateway call was made.",
        file=sys.stderr,
    )
    return 2


def _request(port: int, action: str, actor: str, payload: dict[str, object]) -> int:
    body = json.dumps({"action": action, "actor": actor, "payload": payload}).encode("utf-8")
    request = Request(
        f"http://127.0.0.1:{port}/api/state/apply",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Origin": f"http://127.0.0.1:{os.getenv('QUESTLAB_FRONTEND_PORT', DEFAULT_FRONTEND_PORT)}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            body = error.read().decode("utf-8")
            detail = json.loads(body).get("detail", body)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            detail = error.reason
        print(f"state command rejected: {detail}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, ClientHTTPException, OSError) as error:
        print(f"could not reach local Forge backend: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _get(port: int, path: str) -> int:
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        headers={"Origin": f"http://127.0.0.1:{os.getenv('QUESTLAB_FRONTEND_PORT', DEFAULT_FRONTEND_PORT)}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            body = error.read().decode("utf-8")
            detail = json.loads(body).get("detail", body)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            detail = error.reason
        print(f"state report rejected: {detail}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, ClientHTTPException, OSError) as error:
        print(f"could not reach local Forge backend: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _custody_migrate(port: int, expected_revision: int, confirmation_token: str) -> int:
    body = json.dumps(
        {
            "expected_source_revision": expected_revision,
            "confirmation_token": confirmation_token,
        }
    ).encode("utf-8")
    request = Request(
        f"http://127.0.0.1:{port}/api/state/custody/migrate",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Origin": f"http://127.0.0.1:{os.getenv('QUESTLAB_FRONTEND_PORT', DEFAULT_FRONTEND_PORT)}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            body = error.read().decode("utf-8")
            detail = json.loads(body).get("detail", body)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            detail = error.reason
        print(f"custody migration rejected: {detail}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, ClientHTTPException, OSError) as error:
        print(f"could not reach local Forge backend: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "learning-event":
            payload = {
                "kind": args.kind,
                "evidence_id": _bounded_text(args.evidence_id, "evidence-id", MAX_IDENTIFIER_LENGTH),
                "reason": _bounded_text(args.reason, "reason", MAX_REASON_LENGTH),
            }
            return _request(args.backend_port, "record_learning_event", "pyr", payload)
        if args.command == "reference-mode":
            payload = {
                "milestone_id": _bounded_text(args.milestone_id, "milestone-id", MAX_IDENTIFIER_LENGTH),
                "evidence_id": _bounded_text(args.evidence_id, "evidence-id", MAX_IDENTIFIER_LENGTH),
                "reason": _bounded_text(args.reason, "reason", MAX_REASON_LENGTH),
                "xp_forfeited": args.xp_forfeited,
            }
            return _request(args.backend_port, "record_reference_mode", "pyr", payload)
        if args.command == "homestead-purchase":
            return _request(
                args.backend_port,
                "homestead_purchase",
                "player",
                {"item_id": _bounded_text(args.item_id, "item-id", MAX_IDENTIFIER_LENGTH)},
            )
        if args.command == "homestead-equip":
            return _request(
                args.backend_port,
                "homestead_equip",
                "player",
                {"item_id": _bounded_text(args.item_id, "item-id", MAX_IDENTIFIER_LENGTH)},
            )
        if args.command == "legacy-report":
            return _get(args.backend_port, "/api/state/legacy")
        if args.command == "authority":
            return _get(args.backend_port, "/api/state/revision")
        if args.command == "campaign":
            return _get(args.backend_port, "/api/campaign")
        if args.command == "runtime":
            return _get(args.backend_port, "/api/runtime")
        if args.command == "custody":
            return _get(args.backend_port, "/api/state/custody")
        if args.command == "custody-migrate":
            return _custody_migrate(args.backend_port, args.expected_revision, args.confirm)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    return _reserved(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
