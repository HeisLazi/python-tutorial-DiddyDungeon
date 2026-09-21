from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ide.workspace_transfer import (
    CONFIRM_PULL,
    CONFIRM_PUSH,
    MAX_NOTE_BYTES,
    MAX_NOTE_FILES,
    TransferError,
    _local_payloads,
    _validate_file_name,
    pull,
    push,
    status,
)


def _run(cwd: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


class WorkspaceTransferTests(unittest.TestCase):
    def _git_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": "Quest Lab Test",
                "GIT_AUTHOR_EMAIL": "questlab-test@example.invalid",
                "GIT_COMMITTER_NAME": "Quest Lab Test",
                "GIT_COMMITTER_EMAIL": "questlab-test@example.invalid",
            }
        )
        return env

    def _repo(self, root: Path, name: str) -> Path:
        repo = root / name
        repo.mkdir()
        _run(repo, "init", "-q", "-b", "main")
        _run(repo, "config", "user.name", "Quest Lab Test")
        _run(repo, "config", "user.email", "questlab-test@example.invalid")
        return repo

    def test_push_sanitizes_tree_and_never_uploads_progress_or_private_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bare = root / "remote.git"
            _run(root, "init", "-q", "--bare", str(bare))
            source = self._repo(root, "source")
            (source / "blackjack.py").write_text("print('baseline')\n", encoding="utf-8")
            (source / "tutor.py").write_text("print('tutor baseline')\n", encoding="utf-8")
            (source / "progress.json").write_text('{"player":{"level":1}}\n', encoding="utf-8")
            (source / "SESSION_NOTES.md").write_text("private notes\n", encoding="utf-8")
            _run(source, "add", ".")
            _run(source, "commit", "-qm", "baseline", env=self._git_env())
            _run(source, "remote", "add", "origin", str(bare))
            _run(source, "push", "-q", "origin", "HEAD:refs/heads/01-blackjack", env=self._git_env())

            (source / "blackjack.py").write_text("print('laptop change')\n", encoding="utf-8")
            (source / "tutor.py").write_text("print('laptop tutor')\n", encoding="utf-8")
            (source / "dungeon.py").write_text("# fresh room\n", encoding="utf-8")
            (source / "notes").mkdir()
            (source / "notes" / "lists.md").write_text("# Lists\nUse indexing carefully.\n", encoding="utf-8")
            (source / "notes" / "private.txt").write_text("not a transferable concept note\n", encoding="utf-8")
            (source / ".env").write_text("QUESTLAB_SECRET=do-not-transfer\n", encoding="utf-8")
            (source / "pty.log").write_text("terminal output\n", encoding="utf-8")
            progress_before = (source / "progress.json").read_bytes()
            notes_before = (source / "SESSION_NOTES.md").read_bytes()
            result = push(source, remote_branch="01-blackjack", confirmation=CONFIRM_PUSH)

            self.assertTrue(result["applied"])
            self.assertEqual((source / "progress.json").read_bytes(), progress_before)
            self.assertEqual((source / "SESSION_NOTES.md").read_bytes(), notes_before)
            transfer_sha = _run(source, "ls-remote", "origin", "refs/heads/questlab-files/01-blackjack").split()[0]
            tree_paths = _run(source, "ls-tree", "-r", "--name-only", transfer_sha).splitlines()
            self.assertEqual(
                set(tree_paths),
                {"QUESTLAB_WORKSPACE_TRANSFER.json", "blackjack.py", "tutor.py", "dungeon.py", "notes/lists.md"},
            )
            self.assertNotIn("progress.json", tree_paths)
            self.assertNotIn("SESSION_NOTES.md", tree_paths)
            self.assertNotIn("notes/private.txt", tree_paths)
            self.assertNotIn(".env", tree_paths)
            self.assertNotIn("pty.log", tree_paths)

            manifest = json.loads(_run(source, "show", f"{transfer_sha}:QUESTLAB_WORKSPACE_TRANSFER.json"))
            self.assertEqual(
                {entry["path"] for entry in manifest["files"]},
                {"blackjack.py", "tutor.py", "dungeon.py", "notes/lists.md"},
            )

    def test_pull_updates_allowlisted_files_and_preserves_save(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bare = root / "remote.git"
            _run(root, "init", "-q", "--bare", str(bare))
            source = self._repo(root, "source")
            target = self._repo(root, "target")
            for repo in (source, target):
                (repo / "blackjack.py").write_text("print('baseline')\n", encoding="utf-8")
                (repo / "tutor.py").write_text("print('tutor baseline')\n", encoding="utf-8")
                (repo / "progress.json").write_text('{"player":{"level":2}}\n', encoding="utf-8")
                _run(repo, "add", ".")
                _run(repo, "commit", "-qm", "baseline", env=self._git_env())
            _run(source, "remote", "add", "origin", str(bare))
            _run(target, "remote", "add", "origin", str(bare))
            _run(source, "push", "-q", "origin", "HEAD:refs/heads/01-blackjack", env=self._git_env())
            (source / "blackjack.py").write_text("print('transferred')\n", encoding="utf-8")
            pushed = push(source, remote_branch="01-blackjack", confirmation=CONFIRM_PUSH)
            self.assertTrue(pushed["applied"])

            progress_before = (target / "progress.json").read_bytes()
            result = pull(target, remote_branch="01-blackjack", confirmation=CONFIRM_PULL)
            self.assertTrue(result["applied"])
            self.assertEqual((target / "blackjack.py").read_text(encoding="utf-8"), "print('transferred')\n")
            self.assertEqual((target / "progress.json").read_bytes(), progress_before)

    def test_pull_transfers_concept_notes_and_creates_notes_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bare = root / "remote.git"
            _run(root, "init", "-q", "--bare", str(bare))
            source = self._repo(root, "source")
            target = self._repo(root, "target")
            for repo in (source, target):
                (repo / "blackjack.py").write_text("print('baseline')\n", encoding="utf-8")
                (repo / "tutor.py").write_text("print('tutor baseline')\n", encoding="utf-8")
                (repo / "progress.json").write_text('{"player":{"level":2}}\n', encoding="utf-8")
                _run(repo, "add", ".")
                _run(repo, "commit", "-qm", "baseline", env=self._git_env())
            _run(source, "remote", "add", "origin", str(bare))
            _run(target, "remote", "add", "origin", str(bare))
            _run(source, "push", "-q", "origin", "HEAD:refs/heads/01-blackjack", env=self._git_env())

            (source / "notes").mkdir()
            (source / "notes" / "loops.md").write_text("# Loops\nRepeat while a condition is true.\n", encoding="utf-8")
            pushed = push(source, remote_branch="01-blackjack", confirmation=CONFIRM_PUSH)
            self.assertTrue(pushed["applied"])

            result = pull(target, remote_branch="01-blackjack", confirmation=CONFIRM_PULL)
            self.assertTrue(result["applied"])
            self.assertEqual(
                (target / "notes" / "loops.md").read_text(encoding="utf-8"),
                "# Loops\nRepeat while a condition is true.\n",
            )
            self.assertEqual((target / "progress.json").read_text(encoding="utf-8"), '{"player":{"level":2}}\n')

    def test_pull_refuses_conflict_until_overwrite_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bare = root / "remote.git"
            _run(root, "init", "-q", "--bare", str(bare))
            source = self._repo(root, "source")
            target = self._repo(root, "target")
            for repo in (source, target):
                (repo / "blackjack.py").write_text("print('baseline')\n", encoding="utf-8")
                (repo / "tutor.py").write_text("print('tutor baseline')\n", encoding="utf-8")
                (repo / "progress.json").write_text('{"player":{"level":2}}\n', encoding="utf-8")
                _run(repo, "add", ".")
                _run(repo, "commit", "-qm", "baseline", env=self._git_env())
            _run(source, "remote", "add", "origin", str(bare))
            _run(target, "remote", "add", "origin", str(bare))
            _run(source, "push", "-q", "origin", "HEAD:refs/heads/01-blackjack", env=self._git_env())
            (source / "blackjack.py").write_text("print('remote')\n", encoding="utf-8")
            push(source, remote_branch="01-blackjack", confirmation=CONFIRM_PUSH)
            (target / "blackjack.py").write_text("print('local')\n", encoding="utf-8")

            with self.assertRaisesRegex(TransferError, "allow-overwrite"):
                pull(target, remote_branch="01-blackjack", confirmation=CONFIRM_PULL)
            self.assertEqual((target / "blackjack.py").read_text(encoding="utf-8"), "print('local')\n")

            applied = pull(target, remote_branch="01-blackjack", confirmation=CONFIRM_PULL, allow_overwrite=True)
            self.assertTrue(applied["applied"])
            self.assertEqual((target / "blackjack.py").read_text(encoding="utf-8"), "print('remote')\n")
            backup = Path(applied["backup_directory"])
            self.assertEqual((backup / "blackjack.py").read_text(encoding="utf-8"), "print('local')\n")

    def test_status_reports_protected_and_allowlisted_changes_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = self._repo(root, "workspace")
            (repo / "blackjack.py").write_text("print('x')\n", encoding="utf-8")
            (repo / "progress.json").write_text('{"player":{}}\n', encoding="utf-8")
            (repo / "tutor.py").write_text("print('tutor')\n", encoding="utf-8")
            (repo / "progress.json").write_text('{"player":{"level":3}}\n', encoding="utf-8")
            _run(repo, "add", ".")
            _run(repo, "commit", "-qm", "baseline", env=self._git_env())
            remote = root / "remote.git"
            _run(root, "init", "-q", "--bare", str(remote))
            _run(repo, "remote", "add", "origin", str(remote))
            _run(repo, "push", "-q", "origin", "HEAD:refs/heads/01-blackjack", env=self._git_env())
            (repo / "blackjack.py").write_text("print('dirty')\n", encoding="utf-8")
            (repo / "progress.json").write_text('{"player":{"level":99}}\n', encoding="utf-8")
            report = status(repo, remote_branch="01-blackjack")
            self.assertTrue(any(item["path"] == "blackjack.py" for item in report["allowed_dirty"]))
            self.assertTrue(any(item["path"] == "progress.json" for item in report["blocked_dirty"]))

    def test_note_names_and_limits_are_bounded(self):
        self.assertEqual(_validate_file_name("notes/lists.md"), "notes/lists.md")
        for invalid in ("notes/../progress.json", "notes/a/b.md", "notes\\lists.md", "notes/.md", "notes/lists.txt"):
            with self.assertRaises(TransferError):
                _validate_file_name(invalid)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = self._repo(root, "workspace")
            (repo / "blackjack.py").write_text("print('x')\n", encoding="utf-8")
            (repo / "notes").mkdir()
            (repo / "notes" / "large.md").write_bytes(b"x" * (MAX_NOTE_BYTES + 1))
            with self.assertRaisesRegex(TransferError, "32000"):
                _local_payloads(repo)

    def test_too_many_notes_are_not_transferable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = self._repo(root, "workspace")
            (repo / "blackjack.py").write_text("print('x')\n", encoding="utf-8")
            notes_dir = repo / "notes"
            notes_dir.mkdir()
            for index in range(MAX_NOTE_FILES + 1):
                (notes_dir / f"concept-{index}.md").write_text(f"# Concept {index}\n", encoding="utf-8")
            with self.assertRaisesRegex(TransferError, "64"):
                _local_payloads(repo)


if __name__ == "__main__":
    unittest.main()
