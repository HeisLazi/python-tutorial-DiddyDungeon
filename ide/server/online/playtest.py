"""Disposable loopback-only duel server for trusted local Linux playtesting.

Run: python -m ide.server.online.playtest
Not production: fixed public identities, no real accounts and no durable data.
Never expose this process to a network or use it to evaluate strangers' code.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Prevent accidentally opening the normal service's configured database or
# contacting its account/settlement services in this disposable process.
for _name in tuple(os.environ):
    if _name.startswith('QUESTLAB_ONLINE_'):
        os.environ.pop(_name, None)

from . import service
from .coordinator import DuelCoordinator
from .evaluator import Evaluation, EvaluatorUnavailable
from .worker.cases import CASES
from .worker.sandbox import HARNESS, PRACTICE_HARNESS

GROUP = '00000000-0000-4000-8000-000000000001'
PLAYERS = {'player-one': '00000000-0000-4000-8000-000000000011',
           'player-two': '00000000-0000-4000-8000-000000000022'}

class LocalSandbox:
    """Bubblewrap limits exposure for trusted local testing; not production isolation."""
    def __init__(self):
        if not shutil.which('bwrap') or not shutil.which('prlimit'):
            raise RuntimeError('bubblewrap and prlimit are required; no fallback is provided')
        self.slots = asyncio.Semaphore(2)

    async def run(self, harness: str, payload: dict, limit: int):
        cmd = ['prlimit', '--as=134217728', '--cpu=3:4', '--nproc=4096', '--nofile=32', '--fsize=1048576', '--',
               'bwrap', '--die-with-parent', '--unshare-all', '--new-session',
               '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
               '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--chdir', '/tmp',
               '--clearenv', '--setenv', 'HOME', '/tmp', '--setenv', 'PATH', '/usr/bin',
               '/usr/bin/python3', '-I', '-S', '-c', harness]
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        except OSError as exc:
            raise EvaluatorUnavailable('Local sandbox unavailable.') from exc
        async def transact():
            proc.stdin.write(json.dumps(payload).encode())
            await proc.stdin.drain()
            proc.stdin.close()
            output = bytearray()
            while part := await proc.stdout.read(1024):
                output.extend(part)
                if len(output) > limit:
                    return bytes(output[:limit]), 'output_limit'
            await proc.wait()
            return bytes(output), 'finished'
        try:
            output, reason = await asyncio.wait_for(transact(), timeout=8)
            return output, proc.returncode, reason
        except asyncio.TimeoutError:
            return b'', None, 'timeout'
        except (BrokenPipeError, ConnectionResetError) as exc:
            raise EvaluatorUnavailable('Local sandbox could not start.') from exc
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()

    async def evaluate(self, challenge_id: str, code: str, evaluation_id: str) -> Evaluation:
        if challenge_id not in CASES or not code.strip() or len(code.encode()) > 20000:
            raise ValueError('Invalid submission.')
        passed = True
        async with self.slots:
            for function, args, expected in CASES[challenge_id]:
                data, exit_code, reason = await self.run(HARNESS, {'source': code, 'function': function, 'args': args}, 4096)
                try:
                    result = json.loads(data)
                    ok = reason == 'finished' and exit_code == 0 and type(result) is dict and result.get('type') == type(expected).__name__ and type(result.get('value')) is type(expected) and result['value'] == expected
                except (ValueError, UnicodeDecodeError, KeyError):
                    ok = False
                if not ok:
                    passed = False
                    break
        return Evaluation(passed, 'All checks passed.' if passed else 'Some checks did not pass. Review the function and its edge cases.')

    async def practice(self, code: str, stdin: str, request_id: str) -> dict:
        if not code.strip() or len(code.encode()) > 20000 or len(stdin.encode()) > 4000:
            raise ValueError('Invalid practice request.')
        async with self.slots:
            output, exit_code, reason = await self.run(PRACTICE_HARNESS, {'source': code, 'stdin': stdin}, 6000)
        return {'output': output.decode('utf-8', errors='replace'), 'exit_code': exit_code, 'reason': reason}

async def local_bearer(authorization: str = service.Header(default='')) -> str:
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or token not in PLAYERS:
        raise HTTPException(status_code=401, detail='Select a local playtest player.')
    return token

async def local_group(group_id: str, token: str, other_id: str = '') -> str:
    if group_id != GROUP or token not in PLAYERS or (other_id and other_id not in PLAYERS.values()):
        raise HTTPException(status_code=403, detail='Invalid local playtest group.')
    return PLAYERS[token]

service.app.dependency_overrides[service.bearer] = local_bearer
service.authorize_group = local_group
service.evaluator = LocalSandbox()
service.coordinator = DuelCoordinator(service.evaluator)
service.app.add_middleware(CORSMiddleware, allow_origin_regex=r'http://(localhost|127\.0\.0\.1)(:\d+)?',
    allow_methods=['GET', 'POST'], allow_headers=['authorization', 'content-type'])
app = service.app

@app.middleware('http')
async def local_requests_only(request, call_next):
    from urllib.parse import urlsplit
    from fastapi.responses import JSONResponse
    host = request.headers.get('host', '')
    origin = request.headers.get('origin', '')
    try:
        parsed_host = urlsplit('http://' + host)
        parsed_origin = urlsplit(origin) if origin else None
        safe_host = parsed_host.hostname in ('127.0.0.1', 'localhost') and parsed_host.port == 8911
        safe_origin = not origin or (parsed_origin.scheme == 'http' and parsed_origin.hostname in ('127.0.0.1', 'localhost') and not parsed_origin.username and not parsed_origin.password and not parsed_origin.path and not parsed_origin.query and not parsed_origin.fragment)
    except ValueError:
        safe_host = safe_origin = False
    if not safe_host or not safe_origin:
        return JSONResponse(status_code=403, content={'detail': 'Local playtest only.'})
    return await call_next(request)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8911, access_log=False)
