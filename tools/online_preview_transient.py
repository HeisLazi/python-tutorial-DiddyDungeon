"""Run the real app locally with a disposable save and in-memory cloud config."""
import os
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[1]
key = sys.stdin.readline().strip()
for port in (5173, 7331):
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise SystemExit(f'Port {port} is already in use.')
state_dir = Path(tempfile.mkdtemp(prefix='questlab-online-preview-'))
(state_dir / 'preview-progress.json').write_text(json.dumps({'meta':{'revision':0},'player':{'level':1,'xp':0,'xp_next':100,'coins':0,'hp':100,'max_hp':100},'projects':[]}), encoding='utf-8')
base = {name:os.environ[name] for name in ('PATH','HOME','LANG','DISPLAY','XDG_RUNTIME_DIR') if name in os.environ}
base.update({'QUESTLAB_STATE_PATH':str(state_dir / 'preview-progress.json'), 'QUESTLAB_LOCAL_STATE_ROOT':str(state_dir), 'QUESTLAB_BACKEND_PORT':'7331'})
backend = subprocess.Popen([str(root / '.venv/bin/python'), '-m', 'uvicorn', 'ide.server.app_v2:app', '--host', '127.0.0.1', '--port', '7331'], cwd=root, env=base, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
frontend_env = {**base, 'VITE_QUESTLAB_ONLINE_URL':'https://papasmurff-linux.tail7ca373.ts.net'}
if key and key != '-':
    frontend_env.update({'VITE_SUPABASE_URL':'https://ajnxexxcqfbozszwpjpk.supabase.co', 'VITE_SUPABASE_ANON_KEY':key})
frontend = subprocess.Popen(['npm','run','dev','--','--host','127.0.0.1','--port','5173'], cwd=root / 'ide/frontend', env=frontend_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
for _ in range(120):
    if backend.poll() is not None or frontend.poll() is not None:
        backend.terminate(); frontend.terminate()
        raise SystemExit('The disposable app preview failed to start.')
    try:
        with urllib.request.urlopen('http://127.0.0.1:5173/', timeout=1) as response:
            if response.status == 200:
                print('Disposable app preview ready at http://127.0.0.1:5173/', flush=True)
                break
    except (urllib.error.URLError, TimeoutError):
        time.sleep(.25)
else:
    backend.terminate(); frontend.terminate()
    raise SystemExit('The disposable app preview did not become ready.')
try:
    while backend.poll() is None and frontend.poll() is None:
        time.sleep(1)
finally:
    for child in (backend, frontend):
        if child.poll() is None:
            child.terminate()
