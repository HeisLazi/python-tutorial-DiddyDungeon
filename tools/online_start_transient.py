"""Start the PapaSmurff online host without persisting API credentials.

The publishable Supabase key is read from stdin and passed over Tailscale SSH
through pipes. This starts a detached supervisor; it does not survive reboot.
"""
import json
import shlex
import subprocess
import sys
import tempfile

key = sys.stdin.readline().strip()
if not key:
    raise SystemExit('Missing account configuration on stdin.')
status = json.loads(subprocess.check_output(['tailscale', 'status', '--json']))
peer = next(p for p in status['Peer'].values() if p.get('HostName') == 'papasmurff-linux' and p.get('Online'))
address = next(ip for ip in peer['TailscaleIPs'] if ':' not in ip)
scan = subprocess.run(['ssh-keyscan', '-T', '5', '-t', 'ed25519', address], capture_output=True, text=True, check=True)
remote = r'''
import json,os,subprocess,sys,time,urllib.request
key=sys.stdin.readline().strip()
image=subprocess.check_output(['/usr/bin/docker','-H','unix:///var/run/docker.sock','image','inspect','python:3.12-slim','--format','{{.Id}}'],text=True).strip()
config={'match_user':'lazi','application_root':'/opt/questlab/worker','match_database':'/home/lazi/.local/share/questlab/online/matches.sqlite3','worker_image':image,'publishable_key':key,'supabase_url':'https://ajnxexxcqfbozszwpjpk.supabase.co','allowed_origins':'tauri://localhost,https://tauri.localhost,http://localhost:5173,http://127.0.0.1:5173,http://localhost:7345,http://127.0.0.1:7345','match_port':18918}
try:
 urllib.request.urlopen('http://127.0.0.1:18918/health',timeout=1)
 raise SystemExit('The match port is already in use; no service was started.')
except OSError: pass
p=subprocess.Popen(['/opt/questlab/worker/.venv/bin/python','-m','ide.server.online.host_runner'],cwd='/opt/questlab/worker',stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
p.stdin.write(json.dumps(config).encode());p.stdin.close()
for _ in range(120):
 if p.poll() is not None: raise SystemExit('The online supervisor stopped during startup.')
 try:
  with urllib.request.urlopen('http://127.0.0.1:18918/health',timeout=1) as response: health=json.load(response)
  if all(health.get(k) for k in ('ok','accounts_configured','evaluator_configured','durable_matches')):
   print('Online host is ready on loopback.');break
 except OSError:pass
 time.sleep(.25)
else:
 p.terminate();raise SystemExit('The online host did not become ready.')
'''
with tempfile.NamedTemporaryFile(mode='w') as known:
    known.write(scan.stdout)
    known.flush()
    command = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + known.name,
               'root@' + address, 'python3 -c ' + shlex.quote(remote)]
    result = subprocess.run(command, input=key + '\n', capture_output=True, text=True, timeout=60)
    print(result.stdout[:1000], end='')
    if result.returncode:
        print(result.stderr[:1000], file=sys.stderr)
        raise SystemExit(result.returncode)
