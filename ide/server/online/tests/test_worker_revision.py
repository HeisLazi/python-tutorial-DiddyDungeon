"""The long-running supervisor must keep working when the code on disk is swapped.

host_runner imports `content_revision` once, at supervisor start, and cannot be restarted
without its in-memory credentials. Its startup check sends that revision to a freshly
started worker; if the worker's value differed, every deploy that adds challenge cases
would be rejected and rolled back.
"""
import unittest

from fastapi.testclient import TestClient

from ide.server.online.content_revision import WORKER_REVISION, chain_revision
from ide.server.online.challenges import CHAINS
from ide.server.online.worker import service as worker_service

# The value the supervisor started with on 2026-11-09. Do not change it without
# restarting the supervisor.
SUPERVISOR_REVISION = '3ed48b5044b4170675d8b0f114daada4e82f26c74af8526e6e1036a65b2af4ba'


class StubSandbox:
    async def evaluate(self, challenge_id, source):
        return True


class WorkerRevisionGate(unittest.TestCase):
    def setUp(self):
        self.old = (worker_service.SECRET, worker_service.worker)
        worker_service.SECRET = 's' * 40
        worker_service.worker = StubSandbox()
        self.client = TestClient(worker_service.app)  # no `with`: skip the gVisor lifespan check

    def tearDown(self):
        worker_service.SECRET, worker_service.worker = self.old

    def post(self, revision, challenge_id='potion-afford'):
        return self.client.post('/evaluate', headers={'Authorization': 'Bearer ' + 's' * 40},
                                json={'challenge_id': challenge_id, 'evaluation_id': 'startup-check',
                                      'source': 'def f(): pass', 'revision': revision})

    def test_worker_revision_is_unchanged_by_new_cases(self):
        self.assertEqual(WORKER_REVISION, SUPERVISOR_REVISION)

    def test_supervisors_startup_check_is_accepted_by_the_new_worker(self):
        response = self.post(SUPERVISOR_REVISION)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['revision'], SUPERVISOR_REVISION)

    def test_a_different_revision_is_still_rejected(self):
        self.assertEqual(self.post('f' * 64).status_code, 503)

    def test_new_challenges_are_evaluated_under_the_same_revision(self):
        self.assertEqual(self.post(SUPERVISOR_REVISION, 'advanced-score').status_code, 200)

    def test_new_content_still_changes_each_chains_own_revision(self):
        revisions = {name: chain_revision(chain) for name, chain in CHAINS.items()}
        self.assertEqual(len(set(revisions.values())), len(revisions))


if __name__ == '__main__':
    unittest.main()
