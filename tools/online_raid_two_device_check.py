"""Run the live co-op raid through two authenticated clients.

Provide a dedicated two-account test group and disposable test accounts as one
JSON line on stdin with ``key``, ``group_id``, ``email_a``, ``password_a``,
``email_b``, and ``password_b``. Values are kept in memory, never logged or
saved. The test completes a raid, grants its normal 100 Wazi Bucks reward to
both accounts, and purchases Cinder Vow for account A; do not point it at a
personal group or account.
"""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid


SUPABASE = "https://ajnxexxcqfbozszwpjpk.supabase.co"
MATCH = "https://papasmurff-linux.tail7ca373.ts.net"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(target: str, path: str, token: str = "", body=None):
    headers = {"apikey": API_KEY} if target == SUPABASE else {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        target + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
    )
    try:
        with OPENER.open(request, timeout=65) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Request to {path.split('?')[0]} returned HTTP {error.code}.") from None


def main() -> None:
    global API_KEY
    config = json.loads(sys.stdin.readline())
    API_KEY = config["key"]
    group_id = str(uuid.UUID(config["group_id"]))
    accounts = (
        {"email": config["email_a"], "password": config["password_a"]},
        {"email": config["email_b"], "password": config["password_b"]},
    )

    peer = next(
        item for item in json.loads(subprocess.check_output(["tailscale", "status", "--json"]))["Peer"].values()
        if item.get("HostName") == "papasmurff-linux" and item.get("Online")
    )
    address = next(ip for ip in peer["TailscaleIPs"] if ":" not in ip)
    scan = subprocess.run(
        ["ssh-keyscan", "-T", "5", "-t", "ed25519", address],
        capture_output=True,
        text=True,
        check=True,
    )
    remote = r'''
import json,sys,urllib.error,urllib.request
c=json.load(sys.stdin);target=c['target'];headers={'apikey':c['key']} if 'supabase.co' in target else {}
if c.get('token'):headers['Authorization']='Bearer '+c['token']
if c.get('body') is not None:headers['Content-Type']='application/json'
req=urllib.request.Request(target+c['path'],data=json.dumps(c['body']).encode() if c.get('body') is not None else None,headers=headers)
try:
 with urllib.request.urlopen(req,timeout=65) as response:print(response.read().decode())
except urllib.error.HTTPError as error:print(json.dumps({'_http_error':error.code}))
'''
    with tempfile.NamedTemporaryFile(mode="w") as known_hosts:
        known_hosts.write(scan.stdout)
        known_hosts.flush()

        def other(target: str, path: str, token: str = "", body=None):
            command = [
                "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                "-o", "UserKnownHostsFile=" + known_hosts.name,
                "lazi@" + address, "python3 -c " + shlex.quote(remote),
            ]
            payload = {"target": target, "path": path, "token": token, "body": body}
            if target == SUPABASE:
                payload["key"] = API_KEY
            result = subprocess.run(
                command, input=json.dumps(payload), capture_output=True, text=True, timeout=80
            )
            if result.returncode:
                raise RuntimeError("The second device could not complete its request.")
            data = json.loads(result.stdout)
            if isinstance(data, dict) and "_http_error" in data:
                raise RuntimeError(f"Request to {path.split('?')[0]} returned HTTP {data['_http_error']}.")
            return data

        sessions = []
        for index, account in enumerate(accounts):
            payload = {"email": account["email"], "password": account["password"]}
            if index == 0:
                result = request(SUPABASE, "/auth/v1/token?grant_type=password", body=payload)
            else:
                result = other(SUPABASE, "/auth/v1/token?grant_type=password", body=payload)
            sessions.append({"token": result["access_token"], "user_id": result["user"]["id"]})

        encoded_group = urllib.parse.quote(group_id, safe="-")
        roster_path = (
            "/rest/v1/hunter_group_members?select=user_id&group_id=eq." + encoded_group
        )
        roster = request(SUPABASE, roster_path, sessions[0]["token"])
        expected = {session["user_id"] for session in sessions}
        if {row["user_id"] for row in roster} != expected:
            raise RuntimeError("The supplied group must contain exactly the two disposable test accounts.")

        baseline_wallets = [
            request(MATCH, "/groups/" + group_id + "/wallet", session["token"])
            for session in sessions
        ]

        base = "/groups/" + group_id + "/raids"
        active = request(MATCH, base + "/active", sessions[0]["token"])["raid"]
        if active:
            raise RuntimeError("The disposable test group already has an active raid; no changes were made.")
        raid = request(MATCH, base, sessions[0]["token"], {})
        raid_id = raid["raid_id"]
        if raid["creator_id"] != sessions[0]["user_id"] or raid["status"] != "active":
            raise RuntimeError("The raid did not enter its expected fresh state.")
        if len(raid["tasks"]) != 4:
            raise RuntimeError("The live raid did not expose all four coding tasks.")

        counts = {member: 0 for member in expected}
        for task in raid["tasks"]:
            if task["assignee"] not in counts:
                raise RuntimeError("A task was assigned outside the two-person test roster.")
            counts[task["assignee"]] += 1
        if sorted(counts.values()) != [2, 2]:
            raise RuntimeError("The two-member task distribution was not even.")

        path = base + "/" + raid_id
        first_task = raid["tasks"][0]
        original_owner = first_task["assignee"]
        volunteer = next(member for member in expected if member != original_owner)
        owner_index = next(i for i, item in enumerate(sessions) if item["user_id"] == original_owner)
        volunteer_index = next(i for i, item in enumerate(sessions) if item["user_id"] == volunteer)
        task_body = {"task_id": first_task["id"]}
        opened = request(MATCH, path + "/volunteer/open", sessions[owner_index]["token"], task_body)
        if not opened["tasks"][0]["volunteer_open"]:
            raise RuntimeError("Opening the task for volunteers did not update the shared board.")
        claimed = other(MATCH, path + "/volunteer/claim", sessions[volunteer_index]["token"], task_body)
        if claimed["tasks"][0]["assignee"] != volunteer:
            raise RuntimeError("The second device could not claim the volunteer task.")
        restored = request(MATCH, path + "/assign", sessions[0]["token"],
                          {**task_body, "target_id": original_owner})
        if restored["tasks"][0]["assignee"] != original_owner:
            raise RuntimeError("The creator could not restore the volunteer assignment.")

        second_owner_task = next(
            task for task in raid["tasks"][1:]
            if task["assignee"] != original_owner
        )
        swapped = request(
            MATCH, path + "/swap", sessions[0]["token"],
            {"task_id": first_task["id"], "other_task_id": second_owner_task["id"]},
        )
        if swapped["tasks"][0]["assignee"] != second_owner_task["assignee"]:
            raise RuntimeError("The live task swap did not persist.")
        tasks_after_swap = swapped["tasks"]

        source_by_task = {
            "repair-reward": "def chest_reward(gold, reward):\n    return gold + reward\n",
            "lock-check": "def chest_reward(gold, reward, opened):\n    if opened:\n        return gold + reward\n    return gold\n",
            "collect-chests": (
                "def chest_reward(gold, reward, opened):\n    if opened:\n        return gold + reward\n    return gold\n\n"
                "def collect_chests(gold, chests):\n    for reward, opened in chests:\n        gold = chest_reward(gold, reward, opened)\n    return gold\n"
            ),
            "refund-boundary": (
                "def refund_chest(gold, refund):\n"
                "    return max(0, gold - refund) if refund > 0 else gold\n"
            ),
        }
        for task in tasks_after_swap:
            assignee = task["assignee"]
            submitter = next(i for i, item in enumerate(sessions) if item["user_id"] == assignee)
            reviewer = 1 - submitter
            payload = {"task_id": task["id"], "request_id": "accept-" + task["id"],
                       "code": source_by_task[task["id"]]}
            state = request(MATCH, path + "/submit", sessions[submitter]["token"], payload)
            state = other(MATCH, path, sessions[reviewer]["token"])
            row = next(item for item in state["tasks"] if item["id"] == task["id"])
            if row["status"] != "submitted" or row["passed"] is not True:
                raise RuntimeError("The other client did not receive the verified task submission.")
            state = other(MATCH, path + "/review", sessions[reviewer]["token"],
                          {"task_id": task["id"], "decision": "approve"})
            row = next(item for item in state["tasks"] if item["id"] == task["id"])
            if row["status"] != "accepted":
                raise RuntimeError("Peer review did not advance the shared raid board.")
            state = request(MATCH, path, sessions[submitter]["token"])
            if state["status"] not in ("active", "boss_ready"):
                raise RuntimeError("The raid left its expected coding stage.")

        request(MATCH, path + "/boss/start", sessions[0]["token"], {})
        boss_code = "def can_buy(balance, price):\n    return balance >= price\n"
        purchase_code = boss_code + (
            "\ndef buy_potion(balance, price):\n"
            "    if price >= 0 and can_buy(balance, price):\n        return balance - price\n"
            "    return balance\n"
        )
        single_miss = request(
            MATCH, path + "/boss/submit", sessions[0]["token"],
            {"question_id":"potion-afford", "request_id":"boss-single-miss", "code":"def can_buy(: pass"},
        )
        if (single_miss["boss"]["last_attack"]["type"] != "single" or
                single_miss["boss"]["hunter_hp"][sessions[0]["user_id"]] != 4 or
                single_miss["boss"]["hunter_hp"][sessions[1]["user_id"]] != 5):
            raise RuntimeError("An ordinary boss mistake did not stay single-target.")
        for index, (question, code) in enumerate((
            ("potion-afford", boss_code), ("potion-purchase", purchase_code),
        )):
            player = sessions[index % 2]
            state = request(MATCH, path + "/boss/submit", player["token"],
                            {"question_id": question, "request_id": "boss-" + question, "code": code})
            if index == 1:
                if not state["boss"]["feint_pending"]:
                    raise RuntimeError("The Chief's sarcasm feint did not appear.")
                state = other(MATCH, path + "/boss/feint", player["token"],
                              {"decision": "stand_firm"})
                if state["boss"]["hp"] != 10:
                    raise RuntimeError("Holding firm did not apply the expected feint damage.")

        missed_mechanic = request(
            MATCH, path + "/boss/submit", sessions[0]["token"],
            {"question_id":"potion-negative", "request_id":"boss-aoe-miss", "code":"broken"},
        )
        hp = missed_mechanic["boss"]["hunter_hp"]
        if (missed_mechanic["boss"]["last_attack"]["type"] != "aoe" or
                hp[sessions[0]["user_id"]] != 3 or hp[sessions[1]["user_id"]] != 4):
            raise RuntimeError("Missing the marked mechanic did not damage both hunters.")
        final_code = purchase_code + "\n# A negative refund cannot increase gold.\n"
        completed = other(
            MATCH, path + "/boss/submit", sessions[0]["token"],
            {"question_id": "potion-negative", "request_id": "boss-potion-negative", "code": final_code},
        )
        if completed["status"] != "completed" or not completed["reward_recorded"]:
            raise RuntimeError("The Chief did not settle the completed raid.")
        confirmed = request(MATCH, path, sessions[1]["token"])
        wallets = [
            request(MATCH, "/groups/" + group_id + "/wallet", session["token"])
            for session in sessions
        ]
        expected_earnings = [wallet["earned"]["raid"] + 100 for wallet in baseline_wallets]
        if (confirmed["status"] != "completed" or
                [wallet["earned"]["raid"] for wallet in wallets] != expected_earnings):
            raise RuntimeError("The second client or reward ledger missed the completed raid.")

        shop = other(MATCH, "/groups/" + group_id + "/merchant", sessions[1]["token"])
        item = next((item for item in shop["catalog"] if item["id"] == "online-cinder-vow"), None)
        if not item or item["mode_eligibility"] != ["campaign", "sparring", "pvp"]:
            raise RuntimeError("The online trinket catalog or its mode eligibility is incorrect.")
        merchant_a = request(MATCH, "/groups/" + group_id + "/merchant", sessions[0]["token"])
        purchase_path = "/groups/" + group_id + "/merchant/purchase"
        was_owned = item["id"] in merchant_a["owned_ids"]
        wallet_before_purchase = merchant_a["wallet"]["balance"]
        purchase = request(MATCH, purchase_path, sessions[0]["token"], {"item_id":item["id"]})
        retry = other(MATCH, purchase_path, sessions[0]["token"], {"item_id":item["id"]})
        should_charge = 0 if was_owned else 60
        if (purchase["purchase"]["purchased"] == was_owned or retry["purchase"]["purchased"] or
                purchase["wallet"]["balance"] != wallet_before_purchase - should_charge or
                purchase["wallet"]["balance"] != retry["wallet"]["balance"] or
                item["id"] not in retry["owned_ids"]):
            raise RuntimeError("The online merchant purchase or idempotent retry failed.")
        for mode in ("friendly", "geared"):
            loadouts = request(
                MATCH, "/groups/" + group_id + "/loadouts?mode=" + mode, sessions[0]["token"]
            )
            if item["id"] not in {gear["id"] for gear in loadouts["catalog"]["trinket"]}:
                raise RuntimeError("The purchased trinket is missing from an eligible PvP loadout.")
        print("Two authenticated devices completed the raid, shared reward, idempotent online purchase and eligible PvP loadout checks.")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Two-device raid check stopped: {error}", file=sys.stderr)
        raise SystemExit(1)
