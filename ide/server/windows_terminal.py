"""Windows ConPTY bridge for Quest Lab's existing terminal websocket protocol."""
from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect


async def run_windows_terminal(websocket: WebSocket, shell: str, workspace: Path, env: dict[str, str]) -> None:
    try:
        from winpty import PtyProcess
        process = await asyncio.to_thread(
            PtyProcess.spawn, [shell], cwd=str(workspace), env=env, dimensions=(30, 120)
        )
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        await websocket.send_text(f"\r\n[Quest Lab] Could not start the Windows terminal: {exc}\r\n")
        await websocket.close(code=1011)
        return

    async def output() -> None:
        while True:
            try:
                data = await asyncio.to_thread(process.read, 4096)
                if data:
                    await websocket.send_text(data)
            except (EOFError, OSError, WebSocketDisconnect, RuntimeError):
                return

    async def input_() -> None:
        while True:
            try:
                text = await websocket.receive_text()
            except WebSocketDisconnect:
                return
            try:
                message = json.loads(text) if text.startswith("{") else None
            except json.JSONDecodeError:
                message = None
            if isinstance(message, dict) and message.get("type") == "resize":
                try:
                    cols = max(20, min(int(message.get("cols", 120)), 500))
                    rows = max(5, min(int(message.get("rows", 30)), 200))
                    await asyncio.to_thread(process.setwinsize, rows, cols)
                except (OSError, TypeError, ValueError):
                    pass
                continue
            if isinstance(message, dict):
                if message.get("type") != "input":
                    continue
                payload = message.get("data", "")
            else:
                payload = text
            if isinstance(payload, str) and payload:
                try:
                    await asyncio.to_thread(process.write, payload)
                except (EOFError, OSError):
                    return

    tasks = {asyncio.create_task(output()), asyncio.create_task(input_())}
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*done, *pending, return_exceptions=True)
    finally:
        for task in tasks:
            task.cancel()
        # Unblock pywinpty's socket reader before waiting for the child to exit.
        try:
            process.fileobj.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            await asyncio.to_thread(process.close, True)
        except OSError:
            pass
