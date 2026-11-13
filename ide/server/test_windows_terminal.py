import asyncio
import json
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import WebSocketDisconnect

from ide.server.windows_terminal import run_windows_terminal


class FakeProcess:
    def __init__(self):
        self.fileobj = self
        self.stopped = threading.Event()
        self.writes = []
        self.sizes = []
        self.closed = False

    def read(self, size):
        self.stopped.wait(2)
        raise EOFError()

    def write(self, text):
        self.writes.append(text)

    def setwinsize(self, rows, cols):
        self.sizes.append((rows, cols))

    def shutdown(self, how):
        self.stopped.set()

    def close(self, force):
        self.closed = force


class FakeWebSocket:
    def __init__(self, messages):
        self.messages = iter(messages)
        self.sent = []
        self.close_code = None

    async def receive_text(self):
        try:
            return next(self.messages)
        except StopIteration:
            raise WebSocketDisconnect()

    async def send_text(self, text):
        self.sent.append(text)

    async def close(self, code):
        self.close_code = code


class WindowsTerminalTests(unittest.IsolatedAsyncioTestCase):
    async def test_input_resize_and_disconnect_close_child(self):
        process = FakeProcess()
        spawn_calls = []

        def spawn(*args, **kwargs):
            spawn_calls.append((args, kwargs))
            return process

        winpty = types.SimpleNamespace(PtyProcess=types.SimpleNamespace(spawn=spawn))
        ws = FakeWebSocket([
            json.dumps({"type": "resize", "cols": 900, "rows": 2}),
            json.dumps({"type": "input", "data": "echo hello\r"}),
            json.dumps({"type": "ping"}),
        ])
        with patch.dict(sys.modules, {"winpty": winpty}):
            await asyncio.wait_for(run_windows_terminal(ws, "cmd.exe", Path("workspace"), {"PATH": "x"}), 3)
        self.assertEqual(spawn_calls[0][0], (["cmd.exe"],))
        self.assertEqual(spawn_calls[0][1]["dimensions"], (30, 120))
        self.assertEqual(process.sizes, [(5, 500)])
        self.assertEqual(process.writes, ["echo hello\r"])
        self.assertTrue(process.closed)

    async def test_missing_winpty_reports_failure(self):
        ws = FakeWebSocket([])
        with patch.dict(sys.modules, {"winpty": None}):
            await run_windows_terminal(ws, "cmd.exe", Path("workspace"), {})
        self.assertEqual(ws.close_code, 1011)
        self.assertIn("Could not start the Windows terminal", ws.sent[0])


if __name__ == "__main__":
    unittest.main()
