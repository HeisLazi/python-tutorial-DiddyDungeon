"""Smoke-check candidate online code on PapaSmurff without touching its DB."""
from __future__ import annotations

import io
from pathlib import Path
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ide/server/online"
REMOTE = r'''import asyncio,io,json,os,pathlib,pwd,secrets,shutil,sqlite3,subprocess,sys,tarfile,tempfile,time,urllib.error,urllib.request
project=pathlib.Path('/opt/questlab/worker')
base=pathlib.Path(tempfile.mkdtemp(prefix='questlab-candidate-',dir='/tmp'))
stage=base/'src'
stage.mkdir()
try:
 with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as archive:
  members=archive.getmembers()
  if any(not m.isfile() or pathlib.PurePosixPath(m.name).is_absolute() or '..' in pathlib.PurePosixPath(m.name).parts for m in members): raise SystemExit('Invalid candidate archive.')
  archive.extractall(stage,members=members)
 server=stage/'ide/server'
 for item in (project/'ide/server').iterdir():
  destination=server/item.name
  if item.name!='online' and not destination.exists(): destination.symlink_to(item,target_is_directory=item.is_dir())
 (stage/'.venv').symlink_to(project/'.venv',target_is_directory=True)
 image=subprocess.check_output(['/usr/bin/docker','-H','unix:///var/run/docker.sock','image','inspect','python:3.12-slim','--format','{{.Id}}'],text=True).strip()
 secret=secrets.token_urlsafe(48)
 env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','PYTHONUNBUFFERED':'1','PYTHONPATH':str(stage),
  'QUESTLAB_WORKER_SECRET':secret,'QUESTLAB_WORKER_IMAGE_ID':image}
 run=base/'worker-run'; run.mkdir(mode=0o700)
 socket=run/'worker.sock'
 proc=subprocess.Popen([str(stage/'.venv/bin/python'),'-m','uvicorn','ide.server.online.worker.service:app','--uds',str(socket),'--no-access-log'],cwd=stage,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 try:
  for _ in range(100):
   if proc.poll() is not None: break
   if socket.exists(): break
   time.sleep(.1)
  if proc.poll() is not None:
   lines=proc.stderr.read().decode(errors='replace').splitlines()
   raise SystemExit('Candidate evaluator worker failed to start: '+(lines[-1] if lines else 'unknown startup error'))
  if not socket.exists(): raise SystemExit('Candidate evaluator socket did not appear.')
  probe_env={**env,'QUESTLAB_ONLINE_EVALUATOR_URL':'unix://'+str(socket),'QUESTLAB_ONLINE_EVALUATOR_SECRET':secret}
  code='import asyncio,json,os,sys; from ide.server.online.evaluator import IsolatedEvaluator; r=asyncio.run(IsolatedEvaluator(os.environ["QUESTLAB_ONLINE_EVALUATOR_URL"],os.environ["QUESTLAB_ONLINE_EVALUATOR_SECRET"]).evaluate("potion-afford","def can_buy(balance, price): return balance >= price","candidate-startup")); print(json.dumps({"evaluation_passed":r.passed})); sys.exit(0 if r.passed else 1)'
  check=subprocess.run([str(stage/'.venv/bin/python'),'-c',code],cwd=stage,env=probe_env,capture_output=True,text=True,timeout=35)
  if check.returncode:
   lines=check.stderr.splitlines()
   raise SystemExit('Candidate evaluator request failed: '+(lines[-1] if lines else 'exit '+str(check.returncode)))
  proc.terminate()
  proc.wait(timeout=10)
  os.chmod(base,0o755)
  dbdir=base/'db'; dbdir.mkdir(); user=pwd.getpwnam('lazi'); os.chown(dbdir,user.pw_uid,user.pw_gid)
  image=subprocess.check_output(['/usr/bin/docker','-H','unix:///var/run/docker.sock','image','inspect','python:3.12-slim','--format','{{.Id}}'],text=True).strip()
  config={'match_user':'lazi','application_root':str(stage),'match_database':str(dbdir/'candidate.sqlite3'),'worker_image':image,
   'publishable_key':'sb_publishable_local_probe','supabase_url':'https://local.invalid',
   'allowed_origins':'http://127.0.0.1:5173','match_port':18919}
  runner_env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/home/lazi','PYTHONPATH':str(stage)}
  proc=subprocess.Popen([str(stage/'.venv/bin/python'),'-m','ide.server.online.host_runner'],cwd=stage,env=runner_env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  proc.stdin.write(json.dumps(config).encode()); proc.stdin.close()
  health=None
  for _ in range(120):
   if proc.poll() is not None: break
   try:
    with urllib.request.urlopen('http://127.0.0.1:18919/health',timeout=1) as response: health=json.load(response)
    if all(health.get(key) for key in ('ok','accounts_configured','evaluator_configured','durable_matches','cooperative_projects')): break
    health=None
   except (OSError,urllib.error.URLError): time.sleep(.1)
  if health is None:
   lines=proc.stderr.read().decode(errors='replace').splitlines() if proc.poll() is not None else []
   error=lines[-1] if lines else 'candidate host runner did not become ready'
   raise SystemExit('Candidate supervisor failed: '+error)
  print(json.dumps({key:health.get(key) for key in ('ok','accounts_configured','evaluator_configured','durable_matches','cooperative_projects')}))
  proc.terminate(); proc.wait(timeout=10)
  source=sqlite3.connect('/home/lazi/.local/share/questlab/online/matches.sqlite3')
  snapshot=sqlite3.connect(str(dbdir/'existing.sqlite3'))
  source.backup(snapshot); snapshot.close(); source.close()
  os.chown(dbdir/'existing.sqlite3',user.pw_uid,user.pw_gid)
  env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/home/lazi','PYTHONPATH':str(stage),
   'QUESTLAB_ONLINE_SUPABASE_URL':'https://local.invalid','QUESTLAB_ONLINE_SUPABASE_PUBLISHABLE_KEY':'sb_publishable_local_probe',
   'QUESTLAB_ONLINE_EVALUATOR_URL':'http://127.0.0.1:9','QUESTLAB_ONLINE_EVALUATOR_SECRET':'local-probe-only',
   'QUESTLAB_ONLINE_MATCH_DB':str(dbdir/'existing.sqlite3'),'QUESTLAB_ONLINE_ALLOWED_ORIGINS':'http://127.0.0.1:5173'}
  proc=subprocess.Popen([str(stage/'.venv/bin/python'),'-m','uvicorn','ide.server.online.service:app','--host','127.0.0.1','--port','18919','--no-access-log'],cwd=stage,env=env,user=user.pw_uid,group=user.pw_gid,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  health=None
  for _ in range(80):
   if proc.poll() is not None: break
   try:
    with urllib.request.urlopen('http://127.0.0.1:18919/health',timeout=1) as response: health=json.load(response)
    break
   except (OSError,urllib.error.URLError): time.sleep(.1)
  if health is None:
   lines=proc.stderr.read().decode(errors='replace').splitlines() if proc.poll() is not None else []
   raise SystemExit('Candidate failed against a read-only copy of the existing database: '+(lines[-1] if lines else 'no health response'))
  print(json.dumps({'existing_database_ok':health.get('ok'),'cooperative_projects':health.get('cooperative_projects')}))
 finally:
  if proc.poll() is None: proc.terminate()
  try: proc.wait(timeout=5)
  except subprocess.TimeoutExpired: proc.kill(); proc.wait()
finally:
 shutil.rmtree(base,ignore_errors=True)
'''


def main() -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for relative in (Path("ide/__init__.py"), Path("ide/server/__init__.py")):
            archive.add(ROOT / relative, arcname=relative)
        for source in sorted(PACKAGE.rglob("*.py")):
            archive.add(source, arcname=Path("ide/server/online") / source.relative_to(PACKAGE))
    result = subprocess.run(
        ["tailscale", "ssh", "root@papasmurff-linux", "python3 -c " + shlex.quote(REMOTE)],
        input=buffer.getvalue(), capture_output=True, timeout=40,
    )
    if result.stdout:
        print(result.stdout.decode(errors="replace")[:1000], end="")
    if result.returncode:
        if result.stderr:
            print(result.stderr.decode(errors="replace")[:1000], file=__import__("sys").stderr, end="")
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
