import unittest
import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from ide.server.online import service
from ide.server.online.evaluator import EvaluatorUnavailable, IsolatedEvaluator
from ide.server.online.content_revision import WORKER_REVISION
from ide.server.online.worker.sandbox import Sandbox, SandboxUnavailable


class BoundaryChecks(unittest.IsolatedAsyncioTestCase):
    async def test_worker_client_does_not_expose_checks_or_worker_feedback(self):
        async def respond(request):
            body = request.read().decode()
            self.assertNotIn('assert ', body)
            return httpx.Response(200, json={'evaluation_id':'job-1', 'passed':False, 'feedback':'private details', 'revision':WORKER_REVISION})
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        try:
            evaluator = IsolatedEvaluator('https://worker.example', 'x' * 40, client=client)
            result = await evaluator.evaluate('potion-afford', 'def can_buy(a,b): return False', 'job-1')
            self.assertFalse(result.passed)
            self.assertNotIn('private', result.feedback)
        finally:
            await client.aclose()

    async def test_worker_client_rejects_unmatched_job(self):
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={'evaluation_id':'different', 'passed':True, 'revision':WORKER_REVISION})))
        try:
            evaluator = IsolatedEvaluator('https://worker.example', 'x' * 40, client=client)
            with self.assertRaises(EvaluatorUnavailable):
                await evaluator.evaluate('potion-afford', 'pass', 'job-1')
        finally:
            await client.aclose()

    async def test_worker_client_requires_https(self):
        with self.assertRaises(EvaluatorUnavailable):
            IsolatedEvaluator('http://example.com', 'x' * 40)
        for url in ('unix://host/tmp/worker.sock', 'unix:///tmp/../worker.sock', 'unix:///tmp/x%2fsock'):
            with self.assertRaises(EvaluatorUnavailable):
                IsolatedEvaluator(url, 'x' * 40)

    @unittest.skipIf(os.name == 'nt', 'Unix domain socket deployment is Linux-only')
    async def test_worker_client_over_private_unix_socket(self):
        async def handle(reader, writer):
            headers = await reader.readuntil(b'\r\n\r\n')
            length = next(int(line.split(b':', 1)[1]) for line in headers.split(b'\r\n') if line.lower().startswith(b'content-length:'))
            request = json.loads(await reader.readexactly(length))
            response = json.dumps({'evaluation_id':request['evaluation_id'], 'passed':True, 'revision':WORKER_REVISION}).encode()
            writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ' + str(len(response)).encode() + b'\r\nConnection: close\r\n\r\n' + response)
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'worker.sock')
            server = await asyncio.start_unix_server(handle, path)
            try:
                result = await IsolatedEvaluator('unix://' + path, 'x' * 40).evaluate('potion-afford', 'pass', 'job-1')
                self.assertTrue(result.passed)
            finally:
                server.close()
                await server.wait_closed()

    async def test_worker_client_rejects_mismatched_content(self):
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={'evaluation_id':'job-1', 'passed':True, 'revision':'0' * 64})))
        try:
            with self.assertRaises(EvaluatorUnavailable):
                await IsolatedEvaluator('https://worker.example', 'x' * 40, client=client).evaluate('potion-afford', 'pass', 'job-1')
        finally:
            await client.aclose()

    async def test_unpinned_sandbox_is_rejected(self):
        with self.assertRaises(SandboxUnavailable):
            Sandbox('python:latest')

    async def test_unverified_sandbox_fails_closed(self):
        with patch('ide.server.online.worker.sandbox.shutil.which', return_value='/usr/bin/docker'):
            sandbox = Sandbox('sha256:' + 'a' * 64)
        with self.assertRaises(SandboxUnavailable):
            await sandbox.evaluate('potion-afford', 'pass')

    async def test_practice_uses_sandbox_without_changing_a_verdict(self):
        from unittest.mock import AsyncMock
        with patch('ide.server.online.worker.sandbox.shutil.which', return_value='/usr/bin/docker'):
            sandbox = Sandbox('sha256:' + 'a' * 64)
        sandbox.checked = True
        with patch.object(sandbox, '_run', AsyncMock(return_value=(b'hello\n', 0, 'finished'))) as run:
            result = await sandbox.practice('print("hello")', '')
        self.assertEqual(result, {'output':'hello\n', 'exit_code':0, 'reason':'finished'})
        self.assertNotIn('passed', result)
        self.assertEqual(run.await_count, 1)

    async def test_evaluator_rejects_wrong_practice_request_id(self):
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={
            'request_id':'other', 'output':'hello', 'exit_code':0, 'reason':'finished'})))
        try:
            evaluator = IsolatedEvaluator('https://worker.example', 'x' * 40, client=client)
            with self.assertRaises(EvaluatorUnavailable):
                await evaluator.practice('print(1)', '', 'correct-id')
        finally:
            await client.aclose()

    async def test_group_authorization_checks_both_accounts(self):
        owner='00000000-0000-4000-8000-000000000001'
        stranger='00000000-0000-4000-8000-000000000002'
        group='00000000-0000-4000-8000-000000000003'
        def handler(request):
            if request.url.path.endswith('/user'):
                return httpx.Response(200, json={'id':owner})
            return httpx.Response(200, json=[{'user_id':owner}])
        original = httpx.AsyncClient
        def factory(*args, **kwargs):
            return original(transport=httpx.MockTransport(handler))
        with patch.object(service, 'SUPABASE_URL', 'https://auth.example'), patch.object(service, 'PUBLISHABLE_KEY', 'public-test'), patch.object(service.httpx, 'AsyncClient', factory):
            self.assertEqual(await service.authorize_group(group, 'session', owner), owner)
            with self.assertRaises(HTTPException) as caught:
                await service.authorize_group(group, 'session', stranger)
            self.assertEqual(caught.exception.status_code, 403)


if __name__ == '__main__':
    unittest.main()

class ServiceFlowChecks(unittest.IsolatedAsyncioTestCase):
    async def test_client_config_never_exposes_secret_keys(self):
        transport = httpx.ASGITransport(app=service.app)
        async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
            with patch.object(service, 'SUPABASE_URL', 'https://example.supabase.co'), patch.object(service, 'PUBLISHABLE_KEY', 'sb_secret_test'):
                self.assertEqual((await client.get('/client-config')).status_code, 503)
            with patch.object(service, 'SUPABASE_URL', 'https://example.supabase.co'), patch.object(service, 'PUBLISHABLE_KEY', 'sb_publishable_test'):
                response = await client.get('/client-config')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['cache-control'], 'no-store')

    async def test_two_authenticated_clients_exchange_without_leaking_source(self):
        from ide.server.online.coordinator import DuelCoordinator
        from ide.server.online.evaluator import Evaluation
        from unittest.mock import AsyncMock
        host='00000000-0000-4000-8000-000000000001'
        guest='00000000-0000-4000-8000-000000000002'
        group='00000000-0000-4000-8000-000000000003'
        class Worker:
            async def evaluate(self, challenge_id, code, evaluation_id):
                return Evaluation(code == 'host-private-source', '')
        async def authorize(_group, token, other_id=''):
            if token == 'host-session': return host
            if token == 'guest-session': return guest
            raise HTTPException(status_code=403, detail='Group membership required.')
        fake = DuelCoordinator(Worker())
        transport = httpx.ASGITransport(app=service.app)
        with patch.object(service, 'SUPABASE_URL', 'https://auth.example'), patch.object(service, 'PUBLISHABLE_KEY', 'public-test'), patch.object(service, 'authorize_group', AsyncMock(side_effect=authorize)), patch.object(service, 'coordinator', fake):
            async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
                h={'Authorization':'Bearer host-session'}
                g={'Authorization':'Bearer guest-session'}
                response=await client.post(f'/groups/{group}/invites', headers=h, json={'guest_id':guest,'chain_id':'potion'})
                self.assertEqual(response.status_code, 200)
                invitation=response.json()['invite_id']
                response=await client.post(f'/groups/{group}/invites/{invitation}/accept',headers=g)
                self.assertEqual(response.status_code, 200)
                match=response.json()['match_id']
                recovered=await client.get(f'/groups/{group}/matches/recoverable',headers=h)
                self.assertEqual(recovered.status_code, 200)
                self.assertEqual(recovered.json()['matches'][0]['match_id'], match)
                denied=await client.get(f'/groups/{group}/matches/recoverable',headers={'Authorization':'Bearer outsider'})
                self.assertEqual(denied.status_code, 403)
                missing=await client.get(f'/groups/{group}/matches/does-not-exist',headers=h)
                self.assertEqual(missing.status_code, 404)
                await client.post(f'/groups/{group}/matches/{match}/loadout',headers=h,json={})
                await client.post(f'/groups/{group}/matches/{match}/loadout',headers=g,json={})
                response=await client.post(f'/groups/{group}/matches/{match}/submit',headers=h,json={'stance':'attack','code':'host-private-source'})
                self.assertEqual(response.status_code, 200)
                other=await client.get(f'/groups/{group}/matches/{match}',headers=g)
                self.assertNotIn('host-private-source', other.text)
                self.assertIsNone(other.json()['exchange'])
                response=await client.post(f'/groups/{group}/matches/{match}/submit',headers=g,json={'stance':'guard','code':'guest-private-source'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['phase'],'exchange')
                self.assertEqual(response.json()['you']['hp'],70)
                self.assertNotIn('host-private-source', response.text)
                cancelled=await client.post(f'/groups/{group}/matches/{match}/cancel',headers=h)
                self.assertEqual(cancelled.json()['phase'],'aborted')
                self.assertIsNone(cancelled.json()['winner'])
