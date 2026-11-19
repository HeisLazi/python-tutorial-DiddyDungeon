"""Deterministic challenge/evaluator revisions for safe deployments."""
from dataclasses import asdict
import hashlib
import json

from .worker.cases import CASES


def _digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


# The long-running host supervisor imports this module once and cannot be restarted
# without its in-memory credentials, so the token it sends to the worker must stay the
# same when the code on disk is swapped. It is therefore the digest of the cases that
# existed when the supervisor started. Cases added later are covered by `chain_revision`
# below, which is what protects stored matches. Change this only together with a
# supervisor restart.
_SUPERVISOR_CASE_IDS = (
    'potion-afford', 'potion-purchase', 'potion-negative',
    'chest-fix', 'chest-locked', 'chest-collect', 'chest-refund',
)
WORKER_REVISION = _digest({case_id: CASES[case_id] for case_id in _SUPERVISOR_CASE_IDS})


def chain_revision(chain) -> str:
    return _digest({'challenges':[asdict(item) for item in chain],
                    'checks':{item.id:CASES.get(item.id) for item in chain}})
