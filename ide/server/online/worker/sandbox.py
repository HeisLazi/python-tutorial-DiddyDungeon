"""Fail-closed gVisor-backed one-case runner.

No host paths are mounted into the container. Requires a pre-installed runsc
Docker runtime and a pre-pulled Python image selected by immutable SHA-256 ID.
This worker must be deployed on an isolated machine, never inside the desktop.
"""
from __future__ import annotations

import asyncio
import json
import re
import secrets
import shutil

from .cases import CASES


class SandboxUnavailable(RuntimeError):
    pass


# This program executes inside gVisor, on an immutable image, without network.
# Untrusted output and exceptions are discarded; the worker compares the typed
# returned value with a private expected value outside the sandbox.
HARNESS = r'''
import contextlib, io, json, sys
request = json.load(sys.stdin)
try:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        scope = {'__name__': '__questlab_answer__'}
        exec(compile(request['source'], '<answer>', 'exec'), scope)
        value = scope[request['function']](*request['args'])
    if type(value) not in (bool, int, str, type(None)):
        raise ValueError('unsupported result type')
    sys.stdout.write(json.dumps({'type': type(value).__name__, 'value': value}))
except BaseException:
    sys.stdout.write('{}')
'''


PRACTICE_HARNESS = r'''
import io, json, sys
request = json.load(sys.stdin)
sys.stdin = io.StringIO(request['stdin'])
exec(compile(request['source'], '<duel.py>', 'exec'), {'__name__': '__main__'})
'''


class Sandbox:
    def __init__(self, image_id: str, parallelism: int = 2):
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id or ''):
            raise SandboxUnavailable('Pin the worker image by immutable SHA-256 ID.')
        if not shutil.which('docker'):
            raise SandboxUnavailable('Docker is unavailable.')
        if not 1 <= parallelism <= 4:
            raise SandboxUnavailable('Invalid worker parallelism.')
        self.image_id = image_id
        self.slots = asyncio.Semaphore(parallelism)
        self.checked = False

    async def check_runtime(self) -> None:
        proc = await asyncio.create_subprocess_exec('docker', 'info', '--format', '{{json .Runtimes}}',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            runtimes = json.loads(out) if proc.returncode == 0 else {}
        except (TimeoutError, json.JSONDecodeError):
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            raise SandboxUnavailable('Cannot inspect the sandbox runtime.')
        if not isinstance(runtimes, dict) or 'runsc' not in runtimes:
            raise SandboxUnavailable('The gVisor runsc runtime is required; no fallback is allowed.')
        self.checked = True

    async def _run(self, harness: str, payload: dict, output_limit: int) -> tuple[bytes, int | None, str]:
        name = 'questlab-eval-' + secrets.token_hex(12)
        command = ['docker', 'run', '--rm', '-i', '--name', name, '--runtime=runsc', '--pull=never',
            '--network=none', '--read-only', '--pids-limit=32', '--memory=96m', '--cpus=0.5',
            '--cap-drop=ALL', '--security-opt=no-new-privileges', '--user=65534:65534',
            '--ulimit=cpu=3:4', '--ulimit=nofile=32:32', '--ulimit=fsize=1048576:1048576',
            '--log-driver=none', '--entrypoint=python3', self.image_id, '-I', '-S', '-c', harness]
        proc = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        encoded = json.dumps(payload).encode()
        async def transact() -> tuple[bytes, str]:
            proc.stdin.write(encoded)
            await proc.stdin.drain()
            proc.stdin.close()
            output = bytearray()
            while True:
                part = await proc.stdout.read(1024)
                if not part: break
                output.extend(part)
                if len(output) > output_limit: return bytes(output[:output_limit]), 'output_limit'
            await proc.wait()
            return bytes(output), 'finished'
        try:
            data, reason = await asyncio.wait_for(transact(), timeout=8)
            if reason == 'finished' and proc.returncode in (125, 126, 127):
                raise SandboxUnavailable('Sandbox failed to start.')
            return data, proc.returncode, reason
        except TimeoutError:
            return b'', None, 'timeout'
        except BrokenPipeError:
            # A process that exits before reading its program cannot be trusted.
            raise SandboxUnavailable('Sandbox failed to start.')
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            cleanup = await asyncio.create_subprocess_exec('docker', 'rm', '-f', name,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            try:
                await asyncio.wait_for(cleanup.wait(), timeout=5)
            except TimeoutError:
                cleanup.kill()
                await cleanup.wait()

    async def _case(self, source: str, function: str, args: list, expected: object) -> bool:
        data, exit_code, reason = await self._run(HARNESS, {'source':source, 'function':function, 'args':args}, 4096)
        if reason != 'finished' or exit_code != 0: return False
        try:
            result = json.loads(data)
            return isinstance(result, dict) and result.get('type') == type(expected).__name__ and type(result.get('value')) is type(expected) and result['value'] == expected
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return False

    async def practice(self, source: str, stdin: str) -> dict:
        if not self.checked:
            raise SandboxUnavailable('The worker runtime has not been verified.')
        if (not isinstance(source, str) or not source.strip() or len(source.encode('utf-8')) > 20000
                or not isinstance(stdin, str) or len(stdin.encode('utf-8')) > 4000):
            raise ValueError('Invalid practice request.')
        async with self.slots:
            output, exit_code, reason = await self._run(PRACTICE_HARNESS, {'source':source, 'stdin':stdin}, 6000)
        return {'output':output.decode('utf-8', errors='replace'), 'exit_code':exit_code, 'reason':reason}

    async def evaluate(self, challenge_id: str, source: str) -> bool:
        if not self.checked:
            raise SandboxUnavailable('The worker runtime has not been verified.')
        if challenge_id not in CASES or not isinstance(source, str) or not source.strip() or len(source.encode('utf-8')) > 20000:
            raise ValueError('Invalid evaluation request.')
        async with self.slots:
            for function, args, expected in CASES[challenge_id]:
                if not await self._case(source, function, args, expected):
                    return False
            return True
