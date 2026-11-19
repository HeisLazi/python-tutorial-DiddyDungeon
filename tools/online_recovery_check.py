"""Exercise a separate PapaSmurff host supervisor; public key arrives on stdin.

The running game service, its database and the user's save are not touched.
"""
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

key = sys.stdin.readline().strip()
if not key:
    raise SystemExit('Missing account configuration on stdin.')
status = json.loads(subprocess.check_output(['tailscale', 'status', '--json']))
peer = next(p for p in status['Peer'].values() if p.get('HostName') == 'papasmurff-linux' and p.get('Online'))
address = next(ip for ip in peer['TailscaleIPs'] if ':' not in ip)
scan = subprocess.run(['ssh-keyscan', '-T', '5', '-t', 'ed25519', address], capture_output=True, text=True, check=True)
remote = r'''
import json,os,pathlib,pwd,shutil,signal,subprocess,sys,tempfile,time,urllib.request
key=sys.stdin.buffer.readline().decode().strip()
source=sys.stdin.buffer.read()
root=pathlib.Path(tempfile.mkdtemp(prefix='questlab-recovery-check-'))
root.chmod(0o755)
proc=None
try:
 app=root/'app';shutil.copytree('/opt/questlab/worker',app,symlinks=True)
 (app/'ide/server/online/host_runner.py').write_bytes(source)
 user=pwd.getpwnam('lazi');data=root/'data';data.mkdir();os.chown(data,user.pw_uid,user.pw_gid)
 image=subprocess.check_output(['/usr/bin/docker','-H','unix:///var/run/docker.sock','image','inspect','python:3.12-slim','--format','{{.Id}}'],text=True).strip()
 config={'match_user':'lazi','application_root':str(app),'match_database':str(data/'test.sqlite3'),'worker_image':image,'publishable_key':key,'supabase_url':'https://ajnxexxcqfbozszwpjpk.supabase.co','allowed_origins':'http://127.0.0.1:5173','match_port':18919}
 proc=subprocess.Popen([str(app/'.venv/bin/python'),'-m','ide.server.online.host_runner'],cwd=app,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 proc.stdin.write(json.dumps(config).encode());proc.stdin.close()
 def children():
  try:return [int(x) for x in pathlib.Path(f'/proc/{proc.pid}/task/{proc.pid}/children').read_text().split()]
  except FileNotFoundError:return []
 def worker():
  for pid in children():
   try:
    if b'ide.server.online.worker.service:app' in pathlib.Path(f'/proc/{pid}/cmdline').read_bytes():return pid
   except FileNotFoundError:pass
 def ready():
  try:
   with urllib.request.urlopen('http://127.0.0.1:18919/health',timeout=1) as response: result=json.load(response)
   return all(result.get(k) for k in ('ok','accounts_configured','evaluator_configured','durable_matches'))
  except (OSError,ValueError):return False
 for _ in range(240):
  if proc.poll() is not None:raise RuntimeError('Test supervisor exited')
  old=worker()
  if old and ready():break
  time.sleep(.25)
 else:raise RuntimeError('Test supervisor failed to start')
 os.kill(old,signal.SIGKILL)
 for _ in range(240):
  if proc.poll() is not None:raise RuntimeError('Test supervisor failed to recover')
  new=worker()
  if new and new!=old and ready():
   print('Separate supervisor restarted the isolated worker and match service successfully.');break
  time.sleep(.25)
 else:raise RuntimeError('Test supervisor did not recover')
finally:
 if proc and proc.poll() is None:
  proc.terminate()
  try:proc.wait(timeout=15)
  except subprocess.TimeoutExpired:proc.kill();proc.wait()
 shutil.rmtree(root)
'''
with tempfile.NamedTemporaryFile(mode='w') as known:
    known.write(scan.stdout)
    known.flush()
    command = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + known.name,
               'root@' + address, 'python3 -c ' + shlex.quote(remote)]
    code = Path(__file__).resolve().parents[1] / 'ide/server/online/host_runner.py'
    result = subprocess.run(command, input=key.encode() + b'\n' + code.read_bytes(), capture_output=True, timeout=180)
    print(result.stdout.decode(errors='replace')[:1000], end='')
    if result.returncode:
        print('Recovery check failed on the host.', file=sys.stderr)
        raise SystemExit(result.returncode)
