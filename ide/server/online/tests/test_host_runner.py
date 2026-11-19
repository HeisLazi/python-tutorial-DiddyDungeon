import contextlib
import io
import unittest
from unittest.mock import patch

from ide.server.online import host_runner


class FakeStop:
    def __init__(self):
        self.stopped = False
        self.waits = []

    def is_set(self):
        return self.stopped

    def wait(self, seconds):
        self.waits.append(seconds)
        return self.stopped


class HostSupervisorTests(unittest.TestCase):
    def test_failed_services_restart_with_bounded_backoff_and_no_credential_output(self):
        event = FakeStop()
        calls = []

        def attempt(config, stop):
            calls.append(config)
            if len(calls) < 4:
                raise RuntimeError(config['publishable_key'])
            stop.stopped = True

        config = {'publishable_key': 'private-test-value'}
        output = io.StringIO()
        with patch.object(host_runner, 'run_once', side_effect=attempt), contextlib.redirect_stderr(output):
            host_runner.supervise(config, event)
        self.assertEqual(len(calls), 4)
        self.assertEqual(event.waits, [1.0, 2.0, 4.0])
        self.assertNotIn(config['publishable_key'], output.getvalue())

    def test_requested_stop_does_not_retry(self):
        event = FakeStop()

        def attempt(_config, stop):
            stop.stopped = True
            raise OSError('shutting down')

        with patch.object(host_runner, 'run_once', side_effect=attempt) as run:
            host_runner.supervise({}, event)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(event.waits, [])


if __name__ == '__main__':
    unittest.main()
