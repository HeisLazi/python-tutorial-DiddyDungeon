"""Client for an independently isolated, trusted Python evaluation service.

This module never starts a local subprocess or falls back to the desktop runner.
The worker resolves challenge IDs against its own immutable check catalogue.
Colocated services may use a Unix socket inside a private directory.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlsplit
import httpx
from .content_revision import WORKER_REVISION


class EvaluatorUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Evaluation:
    passed: bool
    feedback: str


class IsolatedEvaluator:
    def __init__(self, url: str, shared_secret: str, *, client: httpx.AsyncClient | None = None):
        parsed = urlsplit(url)
        self._socket = None
        if parsed.scheme == 'unix':
            path = parsed.path
            if (parsed.netloc or parsed.query or parsed.fragment or not path.startswith('/') or
                    '..' in PurePosixPath(path).parts or len(path.encode()) > 100 or '%' in path):
                raise EvaluatorUnavailable('A valid local evaluator socket is required.')
            self._socket = path
            self._url = 'http://questlab-worker'
        elif parsed.scheme == 'https' and parsed.hostname and not (parsed.username or parsed.password or parsed.query or parsed.fragment):
            self._url = url.rstrip('/')
        else:
            raise EvaluatorUnavailable('A dedicated HTTPS evaluator or local socket is required.')
        if not shared_secret or len(shared_secret) < 32:
            raise EvaluatorUnavailable('The evaluator credential is not configured.')
        self._secret = shared_secret
        self._client = client

    def _new_client(self, timeout: float) -> httpx.AsyncClient:
        transport = httpx.AsyncHTTPTransport(uds=self._socket) if self._socket else None
        return httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=4.0), follow_redirects=False, transport=transport, trust_env=False)

    async def evaluate(self, challenge_id: str, code: str, evaluation_id: str) -> Evaluation:
        if not isinstance(code, str) or not code.strip() or len(code.encode('utf-8')) > 20000:
            raise ValueError('Provide Python code of at most 20 KB.')
        if not challenge_id or not evaluation_id:
            raise ValueError('Missing evaluation information.')
        headers = {'Authorization': f'Bearer {self._secret}'}
        payload = {'challenge_id': challenge_id, 'source': code, 'evaluation_id': evaluation_id, 'revision': WORKER_REVISION}
        owned_client = self._client is None
        client = self._client or self._new_client(65.0)
        try:
            response = await client.post(self._url + '/evaluate', headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if (not isinstance(data, dict) or type(data.get('passed')) is not bool or
                    data.get('evaluation_id') != evaluation_id or data.get('revision') != WORKER_REVISION):
                raise EvaluatorUnavailable('The evaluator returned an invalid response.')
            # Do not pass worker errors or private test values directly to clients.
            return Evaluation(data['passed'], 'All checks passed.' if data['passed'] else 'Some checks did not pass. Review the function and its edge cases.')
        except (httpx.HTTPError, ValueError) as exc:
            raise EvaluatorUnavailable('The isolated evaluator is unavailable.') from exc
        finally:
            if owned_client:
                await client.aclose()

    async def practice(self, code: str, stdin: str, request_id: str) -> dict:
        if (not isinstance(code, str) or not code.strip() or len(code.encode('utf-8')) > 20000
                or not isinstance(stdin, str) or len(stdin.encode('utf-8')) > 4000 or not request_id):
            raise ValueError('Invalid practice request.')
        owned_client = self._client is None
        client = self._client or self._new_client(30.0)
        try:
            response = await client.post(self._url + '/practice', headers={'Authorization': f'Bearer {self._secret}'},
                                         json={'source':code, 'stdin':stdin, 'request_id':request_id})
            response.raise_for_status()
            data = response.json()
            if (not isinstance(data, dict) or data.get('request_id') != request_id
                    or not isinstance(data.get('output'), str) or len(data['output'].encode('utf-8')) > 18000
                    or 'exit_code' not in data or data.get('reason') not in ('finished', 'timeout', 'output_limit')
                    or (data.get('exit_code') is not None and type(data['exit_code']) is not int)):
                raise EvaluatorUnavailable('The evaluator returned an invalid practice response.')
            return {'output':data['output'], 'exit_code':data['exit_code'], 'reason':data['reason']}
        except (httpx.HTTPError, ValueError) as exc:
            raise EvaluatorUnavailable('The isolated evaluator is unavailable.') from exc
        finally:
            if owned_client:
                await client.aclose()
