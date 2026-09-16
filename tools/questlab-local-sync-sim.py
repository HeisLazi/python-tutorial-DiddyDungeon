#!/usr/bin/env python3
"""Exercise bounded Quest Lab sync semantics without a cloud account.

The simulator copies the configured canonical snapshot into two temporary
device caches, models a small compare-and-swap mailbox, and uses the real
``LocalStateService`` for every local import/mutation.  It never writes the
source snapshot, the workspace legacy file, Supabase or any browser metadata.
This is a contract/acceptance aid, not hosted-sync proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

# Keep the script runnable both as ``python -m`` from the repository root and
# as the documented ``python tools/questlab-local-sync-sim.py`` command.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ide.server.state import LocalStateService, StateCommandError


class MailboxConflict(RuntimeError):
    """The simulated cloud mailbox rejected a stale expected revision."""


class FakeMailbox:
    """Small in-memory CAS mailbox matching the hosted row contract."""

    def __init__(self, projection: dict[str, Any]) -> None:
        self._lock = threading.RLock()
        self.projection = deepcopy(projection)
        self.revision = 0

    def read(self) -> tuple[dict[str, Any], int]:
        with self._lock:
            return deepcopy(self.projection), self.revision

    def save(self, projection: dict[str, Any], *, expected_revision: int) -> int:
        with self._lock:
            if expected_revision != self.revision:
                raise MailboxConflict(
                    f"mailbox revision conflict (expected {expected_revision}, found {self.revision})"
                )
            self.projection = deepcopy(projection)
            self.revision += 1
            return self.revision


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_source(path: Path) -> bytes:
    try:
        source_bytes = path.read_bytes()
        value = json.loads(source_bytes.decode("utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"source snapshot could not be read: {path}") from exc
    if not isinstance(value, dict) or not value:
        raise RuntimeError("source snapshot must be a non-empty JSON object")
    return source_bytes


def run_simulation(source_path: Path) -> dict[str, Any]:
    """Run the bounded two-device scenario and return auditable evidence."""

    source_path = Path(source_path).expanduser().resolve()
    source_bytes = _load_source(source_path)
    source_digest = hashlib.sha256(source_bytes).hexdigest()

    with tempfile.TemporaryDirectory(prefix="questlab-sync-sim-") as directory:
        root = Path(directory)
        device_a_path = root / "device-a" / "progress.json"
        device_b_path = root / "device-b" / "progress.json"
        device_a_path.parent.mkdir(parents=True)
        device_b_path.parent.mkdir(parents=True)
        device_a_path.write_bytes(source_bytes)
        device_b_path.write_bytes(source_bytes)

        service_a = LocalStateService(device_a_path, threading.RLock())
        service_b = LocalStateService(device_b_path, threading.RLock())
        initial_projection, initial_metadata = service_a.sync_snapshot()
        initial_revision = int(initial_metadata["revision"])
        initial_player = {
            key: initial_projection.get("player", {}).get(key)
            for key in ("level", "xp", "coins", "lifetime_xp")
        }
        mailbox = FakeMailbox(initial_projection)

        service_a.apply_internal(
            "award_learning_reward",
            {"xp": 1, "coins": 2, "reason": "local sync simulator A", "evidence_id": "sync-sim-a"},
        )
        a_projection_1, a_metadata_1 = service_a.sync_snapshot()
        cloud_revision_1 = mailbox.save(a_projection_1, expected_revision=0)

        cloud_projection_1, _ = mailbox.read()
        b_import = service_b.apply_cloud_projection(
            cloud_projection_1,
            expected_revision=initial_revision,
            cloud_revision=cloud_revision_1,
        )
        b_metadata_1 = service_b.metadata()

        service_a.apply_internal(
            "award_learning_reward",
            {"xp": 2, "coins": 3, "reason": "local sync simulator A second change", "evidence_id": "sync-sim-a-2"},
        )
        a_projection_2, a_metadata_2 = service_a.sync_snapshot()
        cloud_revision_2 = mailbox.save(a_projection_2, expected_revision=cloud_revision_1)

        service_b.apply_internal(
            "award_learning_reward",
            {"xp": 4, "coins": 5, "reason": "offline sync simulator B", "evidence_id": "sync-sim-b-offline"},
        )
        b_metadata_offline = service_b.metadata()
        cloud_projection_2, _ = mailbox.read()
        try:
            service_b.apply_cloud_projection(
                cloud_projection_2,
                expected_revision=b_metadata_1["revision"],
                cloud_revision=cloud_revision_2,
            )
        except StateCommandError as exc:
            if exc.status_code != 409:
                raise
            local_conflict_status = {"status_code": exc.status_code, "detail": exc.detail}
        else:
            raise RuntimeError("stale cloud import unexpectedly overwrote device B")

        # Explicit resolution: keep this device.  The cloud CAS is separate
        # from local cache import, so the choice is visible and auditable.
        b_projection, _ = service_b.sync_snapshot()
        cloud_revision_3 = mailbox.save(b_projection, expected_revision=cloud_revision_2)
        cloud_projection_3, _ = mailbox.read()
        a_metadata_before_resolution = service_a.metadata()
        a_resolution = service_a.apply_cloud_projection(
            cloud_projection_3,
            expected_revision=a_metadata_before_resolution["revision"],
            cloud_revision=cloud_revision_3,
        )
        a_final_projection, a_final_metadata = service_a.sync_snapshot()
        b_final_projection, b_final_metadata = service_b.sync_snapshot()

        source_after_digest = _digest(source_path)
        if source_after_digest != source_digest:
            raise RuntimeError("source snapshot changed during local sync simulation")

        if a_final_projection != b_final_projection:
            raise RuntimeError("explicit device resolution left device projections divergent")
        if a_final_metadata["revision"] != a_metadata_before_resolution["revision"] + 1:
            raise RuntimeError("cloud resolution did not create exactly one local revision")
        if a_resolution.get("event", {}).get("action") != "sync_apply_cloud":
            raise RuntimeError("cloud resolution did not append a sync_apply_cloud event")

        return {
            "ok": True,
            "source_path": str(source_path),
            "source_digest_before": source_digest,
            "source_digest_after": source_after_digest,
            "initial_revision": initial_revision,
            "device_a_revision_after_first_push": int(a_metadata_1["revision"]),
            "device_b_revision_after_cloud_pull": int(b_metadata_1["revision"]),
            "device_a_revision_after_second_push": int(a_metadata_2["revision"]),
            "device_b_revision_after_offline_change": int(b_metadata_offline["revision"]),
            "cloud_revision_after_first_push": cloud_revision_1,
            "cloud_revision_after_second_push": cloud_revision_2,
            "cloud_revision_after_keep_device": cloud_revision_3,
            "conflict": local_conflict_status,
            "resolution": "keep-device",
            "final_revision_a": int(a_final_metadata["revision"]),
            "final_revision_b": int(b_final_metadata["revision"]),
            "final_player": {
                "level": a_final_projection.get("player", {}).get("level"),
                "xp": a_final_projection.get("player", {}).get("xp"),
                "coins": a_final_projection.get("player", {}).get("coins"),
                "lifetime_xp": a_final_projection.get("player", {}).get("lifetime_xp"),
            },
            "initial_player": initial_player,
            "sync_event_action": a_resolution["event"]["action"],
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the disposable local Quest Lab two-device sync simulation.")
    parser.add_argument(
        "--source",
        default=str(REPO_ROOT / "progress.json"),
        help="canonical snapshot to copy read-only into temporary device caches",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        print(json.dumps(run_simulation(Path(args.source)), indent=2, ensure_ascii=False))
    except (RuntimeError, StateCommandError) as exc:
        print(f"local sync simulation failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
