from __future__ import annotations

import unittest
from unittest.mock import patch

from ide import state_cli


class StateCliTests(unittest.TestCase):
    @patch("ide.state_cli._request", return_value=0)
    def test_learning_event_uses_named_pyr_action(self, request):
        self.assertEqual(
            state_cli.main(
                [
                    "--backend-port",
                    "7444",
                    "learning-event",
                    "--kind",
                    "teachback",
                    "--evidence-id",
                    "session-001",
                    "--reason",
                    "Explained lists",
                ]
            ),
            0,
        )
        request.assert_called_once_with(
            7444,
            "record_learning_event",
            "pyr",
            {"kind": "teachback", "evidence_id": "session-001", "reason": "Explained lists"},
        )

    @patch("ide.state_cli._request")
    def test_system_command_is_refused_without_gateway_call(self, request):
        self.assertEqual(
            state_cli.main(["hp-change", "--amount", "-9", "--reason", "battle", "--encounter-id", "enc-001"]),
            2,
        )
        request.assert_not_called()

    @patch("ide.state_cli._get", return_value=0)
    def test_legacy_report_is_read_only_and_uses_backend_authority(self, get):
        self.assertEqual(state_cli.main(["--backend-port", "7444", "legacy-report"]), 0)
        get.assert_called_once_with(7444, "/api/state/legacy")

    @patch("ide.state_cli._get", return_value=0)
    def test_authority_and_campaign_commands_are_read_only_backend_projections(self, get):
        self.assertEqual(state_cli.main(["--backend-port", "7444", "authority"]), 0)
        self.assertEqual(state_cli.main(["--backend-port", "7444", "campaign"]), 0)
        self.assertEqual(
            get.call_args_list,
            [
                ((7444, "/api/state/revision"), {}),
                ((7444, "/api/campaign"), {}),
            ],
        )


if __name__ == "__main__":
    unittest.main()
