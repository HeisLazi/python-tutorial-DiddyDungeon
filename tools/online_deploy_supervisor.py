"""Replace only PapaSmurff's supervisor, with rollback; key travels via stdin."""
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

key = sys.stdin.buffer.readline().strip()
if not key:
    raise SystemExit('Missing account configuration on stdin.')
status = json.loads(subprocess.check_output(['tailscale', 'status', '--json']))
peer = next(p for p in status['Peer'].values() if p.get('HostName') == 'papasmurff-linux' and p.get('Online'))
address = next(ip for ip in peer['TailscaleIPs'] if ':' not in ip)
scan = subprocess.run(['ssh-keyscan', '-T', '5', '-t', 'ed25519', address], capture_output=True, text=True, check=True)
remote = r'''
import json,os,pathlib,signal,subprocess,sys,time,urllib.request
 key=sys.stdin.buffer.readline().decode().strip();source=sys.stdin.buffer.read()
root=pathlib.Path('/opt/questlab/worker');target=root/'ide/server/online/host_runner.py';original=target.read_bytes()
image=subprocess.check_output(['/usr/bin/docker','-H','unix:///var/run/docker.sock','image','inspect','python:3.12-slim','--format','{{.Id}}'],text=True).strip()
worker=pathlib.Path('/opt/questlab/worker/.venv/bin/python').resolve()
service_pids=[]
for entry in pathlib.Path('/proc').iterdir():
 if entry.name.isdigit():
  try:
   command=(entry/'cmdline').read_bytes().split(b'\0')
   if b'ide.server.online.service:app' in command and pathlib.Path(command[0].decode()).resolve()==worker:service_pids.append(entry)
  except (OSError,ValueError,UnicodeError):pass
if len(service_pids)!=1:raise SystemExit('Could not identify exactly one live online service; nothing changed.')
environment={}
for pair in (service_pids[0]/'environ').read_bytes().split(b'\0'):
 if b'=' in pair:
  name,value=pair.split(b'=',1);environment[name.decode(errors='ignore')]=value.decode(errors='strict')
publishable_key=environment.get('QUESTLAB_ONLINE_SUPABASE_PUBLISHABLE_KEY','')
if not publishable_key:raise SystemExit('Existing account configuration is unavailable; nothing changed.')
config={'match_user':'lazi','application_root':str(root),'match_database':'/home/lazi/.local/share/questlab/online/matches.sqlite3','worker_image':image,'publishable_key':key,'supabase_url':'https://ajnxexxcqfbozszwpjpk.supabase.co','allowed_origins':'tauri://localhost,https://tauri.localhost,http://localhost:5173,http://127.0.0.1:5173,http://localhost:7345,http://127.0.0.1:7345','match_port':18918}
matches=[]
for entry in pathlib.Path('/proc').iterdir():
 if entry.name.isdigit():
  try:
   command=(entry/'cmdline').read_bytes().split(b'\0')
   if len(command)>2 and command[1:3]==[b'-m',b'ide.server.online.host_runner'] and pathlib.Path(command[0].decode()).resolve()==(root/'.venv/bin/python').resolve():matches.append(int(entry.name))
  except (OSError,ValueError,UnicodeError):pass
if len(matches)!=1:raise SystemExit('Expected exactly one live Quest Lab supervisor; nothing changed.')
os.kill(matches[0],signal.SIGTERM)
for _ in range(120):
 try:
  if pathlib.Path(f'/proc/{matches[0]}/stat').read_text().split(') ',1)[1].startswith('Z '):break
 except FileNotFoundError:break
 time.sleep(.25)
else:raise SystemExit('Existing supervisor did not stop; nothing changed.')
def start():
 proc=subprocess.Popen([str(root/'.venv/bin/python'),'-m','ide.server.online.host_runner'],cwd=root,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 proc.stdin.write(json.dumps(config).encode());proc.stdin.close()
 for _ in range(180):
  if proc.poll() is not None:break
  try:
   with urllib.request.urlopen('http://127.0.0.1:18918/health',timeout=1) as response:health=json.load(response)
   if all(health.get(k) for k in ('ok','accounts_configured','evaluator_configured','durable_matches')):return proc
  except OSError:pass
  time.sleep(.25)
 if proc.poll() is None:proc.terminate();proc.wait(timeout=15)
 raise RuntimeError('Supervisor failed its startup check')
try:
 target.write_bytes(source);start();print('Updated supervisor is online.')
except Exception:
 target.write_bytes(original)
 try:start();print('Previous supervisor restored after failed update.',file=sys.stderr)
 except Exception:print('Automatic restore failed; manual host recovery is required.',file=sys.stderr)
 raise SystemExit(1)
'''
with tempfile.NamedTemporaryFile(mode='w') as known:
    known.write(scan.stdout)
    known.flush()
    command = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + known.name,
               'root@' + address, 'python3 -c ' + shlex.quote(remote)]
    source = Path(__file__).resolve().parents[1] / 'ide/server/online/host_runner.py'
    result = subprocess.run(command, input=key + b'\n' + source.read_bytes(), capture_output=True, timeout=150)
    print(result.stdout.decode(errors='replace')[:1000], end='')
    if result.returncode:
        print(result.stderr.decode(errors='replace')[:1000], file=sys.stderr)
        raise SystemExit(result.returncode)
