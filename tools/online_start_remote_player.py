"""Start the disposable opponent on PapaSmurff; config travels on stdin."""
import json
import subprocess
import sys
import tempfile

config = sys.stdin.readline()
status = json.loads(subprocess.check_output(['tailscale','status','--json']))
peer = next(p for p in status['Peer'].values() if p.get('HostName') == 'papasmurff-linux' and p.get('Online'))
ip = next(ip for ip in peer['TailscaleIPs'] if ':' not in ip)
scan = subprocess.run(['ssh-keyscan','-T','5','-t','ed25519',ip],capture_output=True,text=True,check=True)
with tempfile.NamedTemporaryFile(mode='w') as known:
    known.write(scan.stdout); known.flush()
    process = subprocess.Popen(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+known.name,'lazi@'+ip,'node /opt/questlab/online-playtest/remote_player.mjs'],stdin=subprocess.PIPE,text=True)
    process.stdin.write(config); process.stdin.close()
    raise SystemExit(process.wait())
