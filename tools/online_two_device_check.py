"""Exercise real authenticated duel APIs from Wazi and PapaSmurff.

Inputs are supplied once over stdin and never written to disk or logged.
The caller owns creation and deletion of the two disposable test accounts.
"""
import json
import shlex
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

config = json.loads(sys.stdin.readline())
key, password = config['key'], config['password']
url = 'https://ajnxexxcqfbozszwpjpk.supabase.co'
match_url = 'https://papasmurff-linux.tail7ca373.ts.net'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def request(target, path, token='', body=None):
    headers = {'apikey':key} if target == url else {}
    if token: headers['Authorization'] = 'Bearer ' + token
    if body is not None: headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(target + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    try:
        with opener.open(req, timeout=35) as response: return json.load(response)
    except urllib.error.HTTPError as exc:
        try: code = json.load(exc).get('error_code', '')
        except (ValueError, AttributeError): code = ''
        raise RuntimeError(f'Request to {path.split("?")[0]} failed with HTTP {exc.code} ({code}).') from exc

peer = next(p for p in json.loads(subprocess.check_output(['tailscale','status','--json']))['Peer'].values() if p.get('HostName') == 'papasmurff-linux')
ip = next(ip for ip in peer['TailscaleIPs'] if ':' not in ip)
scan = subprocess.run(['ssh-keyscan','-T','5','-t','ed25519',ip],capture_output=True,text=True,check=True)
remote = r'''
import json,sys,urllib.request,urllib.error
c=json.load(sys.stdin); opener=urllib.request.build_opener(urllib.request.ProxyHandler({})); target=c['target']; headers={'apikey':c['key']} if 'supabase.co' in target else {}
if c.get('token'): headers['Authorization']='Bearer '+c['token']
if c.get('body') is not None: headers['Content-Type']='application/json'
req=urllib.request.Request(target+c['path'],data=json.dumps(c['body']).encode() if c.get('body') is not None else None,headers=headers)
try:
 with opener.open(req,timeout=35) as response: print(response.read().decode())
except urllib.error.HTTPError as exc:
 print(json.dumps({'_http_error':exc.code}))
'''
with tempfile.NamedTemporaryFile(mode='w') as known:
    known.write(scan.stdout); known.flush()
    def other(target, path, token='', body=None):
        cmd=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+known.name,'lazi@'+ip,'python3 -c '+shlex.quote(remote)]
        result=subprocess.run(cmd,input=json.dumps({'target':target,'path':path,'token':token,'body':body,'key':key}),capture_output=True,text=True,timeout=45)
        if result.returncode: raise RuntimeError(f'Other device request to {path.split("?")[0]} failed.')
        data=json.loads(result.stdout)
        if isinstance(data,dict) and '_http_error' in data: raise RuntimeError(f'Other device request to {path.split("?")[0]} failed with HTTP {data["_http_error"]}.')
        return data

    first = request(url,'/auth/v1/token?grant_type=password',body={'email':config['email_a'],'password':password})['access_token']
    second = other(url,'/auth/v1/token?grant_type=password',body={'email':config['email_b'],'password':password})['access_token']
    group = request(url,'/rest/v1/rpc/create_hunter_group',first,{'group_name':'Temporary network playtest'})
    invite = request(url,'/rest/v1/rpc/create_hunter_group_invite',first,{'target_group':group})
    assert other(url,'/rest/v1/rpc/join_hunter_group',second,{'invitation':invite}) == group
    base = '/groups/' + group
    sent = request(match_url,base+'/invites',first,{'guest_id':config['user_b'],'chain_id':'potion','mode':'fair'})
    match = other(match_url,base+'/invites/'+sent['invite_id']+'/accept',second,{})['match_id']
    path=base+'/matches/'+match
    request(match_url,path+'/loadout',first,{})
    other(match_url,path+'/loadout',second,{})
    code1='def can_buy(balance, price):\n    return balance >= price\n'
    code2=code1+'\ndef buy_potion(balance, price):\n    return balance - price if price >= 0 and can_buy(balance, price) else balance\n'
    for round_index, code in enumerate((code1,code2,code2)):
        request(match_url,path+'/submit',first,{'stance':'attack','code':code})
        result=other(match_url,path+'/submit',second,{'stance':'guard','code':code})
        view=request(match_url,path,first)
        assert result['exchange']['passed'] and view['exchange']['passed']
        assert result['you']['hp']==view['opponent']['hp'] and result['opponent']['hp']==view['you']['hp']
        if round_index < 2:
            request(match_url,path+'/ready',first,{})
            next_view=other(match_url,path+'/ready',second,{})
            if round_index == 0:
                assert next_view['phase']=='bonus'
                request(match_url,path+'/bonus',first,{'answer':0,'reward':'heal'})
                other(match_url,path+'/bonus',second,{'answer':0,'reward':'heal'})
    assert view['phase']=='finished' and result['phase']=='finished' and view['winner']==result['winner']
    print('Authenticated three-round duel completed across Wazi and PapaSmurff; both views agree.')
