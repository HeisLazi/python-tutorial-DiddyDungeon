"""Single-host launcher for a private match service and isolated worker.

Run as root on a dedicated Linux host. Configuration is read once from stdin;
credentials are passed only through process environments, never written to
disk or command-line arguments. The match process runs as an unprivileged user.
If either child exits, the supervisor stops both and retries with bounded
backoff; the private socket and worker credential are recreated each time.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import pwd
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

from .evaluator import Evaluation, EvaluatorUnavailable, IsolatedEvaluator


def run_once(config: dict, stop_event: threading.Event) -> None:
    if os.name != 'posix' or os.geteuid() != 0:
        raise RuntimeError('The isolated host launcher requires Linux root privileges.')
    if not isinstance(config, dict):
        raise RuntimeError('Invalid host configuration.')
    user = pwd.getpwnam(config['match_user'])
    if user.pw_uid == 0:
        raise RuntimeError('The match service must use an unprivileged account.')
    root = Path(config['application_root']).resolve(strict=True)
    python = root / '.venv/bin/python'
    db = Path(config['match_database'])
    if not python.is_file() or not db.is_absolute() or db.name.lower() == 'progress.json':
        raise RuntimeError('Invalid application or match database path.')
    image = config['worker_image']
    if not isinstance(image, str) or len(image) != 71 or not image.startswith('sha256:') or any(c not in '0123456789abcdef' for c in image[7:]):
        raise RuntimeError('The sandbox image must be pinned by SHA-256.')
    public_key = config['publishable_key']
    if not isinstance(public_key, str) or not public_key or len(public_key) > 8192:
        raise RuntimeError('The public account configuration is unavailable.')
    origins = config['allowed_origins']
    if not isinstance(origins, str) or not origins:
        raise RuntimeError('Explicit client origins are required.')

    secret = secrets.token_urlsafe(48)
    env = {'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin', 'LANG':'C.UTF-8', 'PYTHONUNBUFFERED':'1'}
    worker_env = {**env, 'QUESTLAB_WORKER_SECRET':secret, 'QUESTLAB_WORKER_IMAGE_ID':image}
    worker = match = None
    with tempfile.TemporaryDirectory(prefix='questlab-online-', dir='/run') as directory:
        os.chown(directory, user.pw_uid, user.pw_gid)
        os.chmod(directory, 0o700)
        socket = directory + '/worker.sock'
        try:
            worker = subprocess.Popen([str(python), '-m', 'uvicorn', 'ide.server.online.worker.service:app', '--uds', socket, '--no-access-log'], cwd=root, env=worker_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(100):
                if worker.poll() is not None:
                    raise RuntimeError('The isolated evaluator failed to start.')
                if os.path.exists(socket):
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError('The isolated evaluator did not become ready.')
            async def check() -> Evaluation:
                return await IsolatedEvaluator('unix://' + socket, secret).evaluate('potion-afford', 'def can_buy(balance, price): return balance >= price', 'startup-check')
            if not asyncio.run(check()).passed:
                raise RuntimeError('The isolated evaluator failed its startup check.')
            match_env = {**env, 'HOME':user.pw_dir, 'QUESTLAB_ONLINE_SUPABASE_URL':config['supabase_url'],
                'QUESTLAB_ONLINE_SUPABASE_PUBLISHABLE_KEY':public_key, 'QUESTLAB_ONLINE_EVALUATOR_URL':'unix://' + socket,
                'QUESTLAB_ONLINE_EVALUATOR_SECRET':secret, 'QUESTLAB_ONLINE_MATCH_DB':str(db),
                'QUESTLAB_ONLINE_ALLOWED_ORIGINS':origins}
            match = subprocess.Popen([str(python), '-m', 'uvicorn', 'ide.server.online.service:app', '--host', '127.0.0.1', '--port', str(config.get('match_port', 18918)), '--no-access-log'], cwd=root, env=match_env, user=user.pw_uid, group=user.pw_gid, extra_groups=[], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(100):
                if match.poll() is not None:
                    raise RuntimeError('The match service failed to start.')
                try:
                    with urllib.request.urlopen('http://127.0.0.1:' + str(config.get('match_port', 18918)) + '/health', timeout=1) as response:
                        health = json.load(response)
                    if not all(health.get(name) for name in ('ok', 'accounts_configured', 'evaluator_configured', 'durable_matches')):
                        raise RuntimeError('The match service is not fully configured.')
                    break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.1)
            else:
                raise RuntimeError('The match service did not become ready.')
            print('Quest Lab online host ready.', flush=True)
            while not stop_event.is_set() and worker.poll() is None and match.poll() is None:
                stop_event.wait(0.25)
            if not stop_event.is_set():
                raise RuntimeError('An online service stopped unexpectedly.')
        finally:
            for child in (match, worker):
                if child is not None and child.poll() is None:
                    child.terminate()
            for child in (match, worker):
                if child is not None:
                    try: child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill(); child.wait()


def supervise(config: dict, stop_event: threading.Event) -> None:
    """Keep credentials only in memory while restarting the isolated pair."""
    delay = 1.0
    while not stop_event.is_set():
        started = time.monotonic()
        try:
            run_once(config, stop_event)
        except (KeyError, ValueError, OSError, RuntimeError, EvaluatorUnavailable):
            if stop_event.is_set():
                break
            # Do not log config or exception text: an upstream error could
            # include a credential. Repeated failures back off to 30 seconds.
            print('Quest Lab online services stopped; retrying.', file=sys.stderr, flush=True)
            if time.monotonic() - started >= 60:
                delay = 1.0
            stop_event.wait(delay)
            delay = min(delay * 2, 30.0)
        else:
            break


def main() -> None:
    config = json.load(sys.stdin)
    if not isinstance(config, dict):
        raise RuntimeError('Invalid host configuration.')
    stop_event = threading.Event()
    def stop(_signum, _frame):
        stop_event.set()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    supervise(config, stop_event)


if __name__ == '__main__':
    try:
        main()
    except (KeyError, ValueError, OSError, RuntimeError, EvaluatorUnavailable, json.JSONDecodeError) as error:
        print(f'Online host failed: {error}', file=sys.stderr)
        raise SystemExit(1)
