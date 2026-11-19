"""Safely deploy the online package by restarting its config-owning launcher.

All account configuration is copied directly from the live match process into
remote memory and never printed, written to disk, or sent back to this machine.
"""
from __future__ import annotations

import io
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ide/server/online"
REMOTE = r'''import compileall,datetime,io,json,os,pathlib,signal,subprocess,sys,tarfile,tempfile,time,urllib.error,urllib.request
root=pathlib.Path('/opt/questlab/worker');target=root/'ide/server/online';archive=sys.stdin.buffer.read()
if len(archive)>30*1024*1024: raise SystemExit('Package exceeds transfer limit.')
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup=pathlib.Path('/opt/questlab/rollback')/('online-'+stamp);stage=pathlib.Path(tempfile.mkdtemp(prefix='.online-stage-',dir=str(target.parent)));changed=False;new_runner=None
def processes():
 found=[]
 python=(root/'.venv/bin/python').resolve()
 for item in pathlib.Path('/proc').iterdir():
  if not item.name.isdigit(): continue
  try:
   args=(item/'cmdline').read_bytes().split(b'\0')
   if args and pathlib.Path(args[0].decode()).resolve()==python: found.append((int(item.name),args))
  except (OSError,ValueError,UnicodeError): pass
 return found
def match(args): return b'ide.server.online.service:app' in args
def runner_args(args): return len(args)>2 and args[1:3]==[b'-m',b'ide.server.online.host_runner']
def health():
 try:
  with urllib.request.urlopen('http://127.0.0.1:18918/health',timeout=1) as r: return json.load(r)
 except (OSError,urllib.error.URLError,ValueError): return None
def wait_stopped(pid):
 for _ in range(300):
  try:
   state=pathlib.Path('/proc/'+str(pid)+'/stat').read_text().split(') ',1)[1]
   if state.startswith('Z '): return
  except FileNotFoundError: return
  time.sleep(.1)
 raise RuntimeError('Previous launcher did not stop.')
def stop_current():
 global new_runner
 if new_runner is not None and new_runner.poll() is None:
  new_runner.terminate()
  try: new_runner.wait(timeout=30)
  except subprocess.TimeoutExpired: new_runner.kill();new_runner.wait()
 else:
  for pid,args in processes():
   if runner_args(args):
    os.kill(pid,signal.SIGTERM);wait_stopped(pid);break
def probe_evaluator():
 live=processes();match_pids=[pid for pid,args in live if match(args)];worker_pids=[pid for pid,args in live if b'ide.server.online.worker.service:app' in args]
 if len(match_pids)!=1 or len(worker_pids)!=1: raise RuntimeError('Expected one match and one isolated worker after restart.')
 def env_for(pid):
  result={}
  for item in pathlib.Path('/proc/'+str(pid)+'/environ').read_bytes().split(b'\0'):
   if b'=' in item:
    k,v=item.split(b'=',1);result[k.decode(errors='ignore')]=v.decode(errors='strict')
  return result
 match_env=env_for(match_pids[0]);worker_env=env_for(worker_pids[0]);url=match_env.get('QUESTLAB_ONLINE_EVALUATOR_URL','');secret=worker_env.get('QUESTLAB_WORKER_SECRET','')
 if not url.startswith('unix://') or len(secret)<32: raise RuntimeError('Isolated evaluator configuration unavailable after restart.')
 code="""import asyncio,os
from ide.server.online.evaluator import IsolatedEvaluator
async def main():
 e=IsolatedEvaluator(os.environ['QUESTLAB_EVALUATOR_URL'],os.environ['QUESTLAB_WORKER_SECRET'])
 good=await e.evaluate('chest-refund','def refund_chest(gold, refund):\\n    return max(0, gold-refund) if refund > 0 else gold\\n','deploy-good')
 bad=await e.evaluate('chest-refund','def refund_chest(gold, refund):\\n    return gold-refund\\n','deploy-bad')
 if not good.passed or bad.passed: raise SystemExit(2)
asyncio.run(main())
"""
 env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','PYTHONPATH':str(root),'QUESTLAB_EVALUATOR_URL':url,'QUESTLAB_WORKER_SECRET':secret}
 result=subprocess.run([str(root/'.venv/bin/python'),'-c',code],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=150)
 if result.returncode: raise RuntimeError('The deployed isolated refund check did not pass.')
def launch(config):
 global new_runner
 new_runner=subprocess.Popen([str(root/'.venv/bin/python'),'-m','ide.server.online.host_runner'],cwd=root,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 new_runner.stdin.write(json.dumps(config).encode());new_runner.stdin.close()
 for _ in range(240):
  if new_runner.poll() is not None: raise RuntimeError('Launcher stopped before health checks passed.')
  h=health()
  if h and all(h.get(k) is True for k in ('ok','accounts_configured','evaluator_configured','durable_matches','cooperative_projects')):
   probe_evaluator();return
  time.sleep(.25)
 raise RuntimeError('Online service health check timed out.')
try:
 live=processes();matches=[(pid,args) for pid,args in live if match(args)];runners=[(pid,args) for pid,args in live if runner_args(args)]
 if len(matches)!=1 or len(runners)!=1: raise RuntimeError('Expected one live match process and one launcher; nothing changed.')
 env={}
 for item in pathlib.Path('/proc/'+str(matches[0][0])+'/environ').read_bytes().split(b'\0'):
  if b'=' in item:
   k,v=item.split(b'=',1);env[k.decode(errors='ignore')]=v.decode(errors='strict')
 required=('QUESTLAB_ONLINE_SUPABASE_URL','QUESTLAB_ONLINE_SUPABASE_PUBLISHABLE_KEY','QUESTLAB_ONLINE_ALLOWED_ORIGINS')
 if any(not env.get(k) for k in required): raise RuntimeError('Live account configuration unavailable; nothing changed.')
 image=subprocess.check_output(['/usr/bin/docker','-H','unix:///var/run/docker.sock','image','inspect','python:3.12-slim','--format','{{.Id}}'],text=True,stderr=subprocess.DEVNULL).strip()
 if not image.startswith('sha256:'): raise RuntimeError('Pinned worker image unavailable; nothing changed.')
 allowed_origins={origin.strip() for origin in env['QUESTLAB_ONLINE_ALLOWED_ORIGINS'].split(',') if origin.strip()}
 allowed_origins.add('http://tauri.localhost')
 # The desktop launcher falls forward from 7345 when another Quest Lab
 # instance already owns the preferred port. Keep every accepted fallback an
 # exact loopback origin; the game still uses signed-in sessions and group ACLs.
 for port in range(7345,7445):
  allowed_origins.add('http://localhost:'+str(port))
  allowed_origins.add('http://127.0.0.1:'+str(port))
 config={'match_user':'lazi','application_root':str(root),'match_database':env.get('QUESTLAB_ONLINE_MATCH_DB','/home/lazi/.local/share/questlab/online/matches.sqlite3'),'worker_image':image,'publishable_key':env['QUESTLAB_ONLINE_SUPABASE_PUBLISHABLE_KEY'],'supabase_url':env['QUESTLAB_ONLINE_SUPABASE_URL'],'allowed_origins':','.join(sorted(allowed_origins)),'match_port':18918}
 if not target.is_dir() or not (root/'.venv/bin/python').is_file(): raise RuntimeError('Online installation is missing; nothing changed.')
 backup.parent.mkdir(parents=True,exist_ok=True);__import__('shutil').copytree(target,backup)
 with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as bundle:
  members=bundle.getmembers()
  if len(members)>300 or any(not m.isfile() or pathlib.PurePosixPath(m.name).is_absolute() or '..' in pathlib.PurePosixPath(m.name).parts for m in members): raise RuntimeError('Invalid source archive.')
  bundle.extractall(stage,members=members)
 if not (stage/'service.py').is_file() or not compileall.compile_dir(stage,quiet=1,force=True): raise RuntimeError('Online package failed compilation.')
 os.chmod(stage,0o755);retired=target.parent/('.online-previous-'+stamp);os.rename(target,retired);os.rename(stage,target);changed=True
 os.kill(runners[0][0],signal.SIGTERM);wait_stopped(runners[0][0]);launch(config)
 for origin in ('http://tauri.localhost','http://localhost:7345','http://localhost:7348','http://localhost:7444'):
  request=urllib.request.Request('http://127.0.0.1:18918/client-config',headers={'Origin':origin})
  with urllib.request.urlopen(request,timeout=3) as response:
   if response.headers.get('Access-Control-Allow-Origin')!=origin: raise RuntimeError('Desktop CORS check failed.')
 request=urllib.request.Request('http://127.0.0.1:18918/client-config',headers={'Origin':'https://evil.example'})
 with urllib.request.urlopen(request,timeout=3) as response:
  if response.headers.get('Access-Control-Allow-Origin') is not None: raise RuntimeError('Unexpected origin passed the CORS check.')
 print('Updated online service and isolated evaluator are healthy; exact desktop CORS checks passed; rollback copy retained at '+str(backup)+'.')
except Exception as error:
 if changed:
  try:
   stop_current()
   if target.exists(): __import__('shutil').rmtree(target)
   __import__('shutil').copytree(backup,target)
   new_runner=None;launch(config)
   print('Deployment failed; previous package restored and service healthy.',file=sys.stderr)
  except Exception: print('Deployment failed and automatic recovery could not verify the host; backup retained.',file=sys.stderr)
 detail=str(error);print('Online deployment stopped: '+type(error).__name__+(': '+detail if detail and len(detail)<150 else '')+'.',file=sys.stderr);sys.exit(1)
finally:
 if stage.exists(): __import__('shutil').rmtree(stage,ignore_errors=True)
'''


def main() -> None:
    if not PACKAGE.is_dir():
        raise SystemExit("Online source package is missing.")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for source in sorted(PACKAGE.rglob("*.py")):
            archive.add(source, arcname=source.relative_to(PACKAGE))
    if not buffer.tell():
        raise SystemExit("Online source package is empty.")
    command = ["tailscale", "ssh", "root@papasmurff-linux", "python3 -c " + shlex.quote(REMOTE)]
    result = subprocess.run(command, input=buffer.getvalue(), capture_output=True, timeout=350)
    if result.stdout:
        print(result.stdout.decode(errors="replace")[:2000], end="")
    if result.returncode:
        if result.stderr:
            print(result.stderr.decode(errors="replace")[:2000], file=sys.stderr, end="")
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
