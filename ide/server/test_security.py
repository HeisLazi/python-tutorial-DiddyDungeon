from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from ide.server import app_v2
from ide.server.security import allowed_origins


class LocalSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app_v2.app, base_url="http://127.0.0.1")

    def test_trusted_host_rejects_untrusted_host(self):
        response = self.client.get("/api/health", headers={"host": "evil.example"})
        self.assertEqual(response.status_code, 400)

    def test_hostile_websocket_origin_is_rejected(self):
        with self.assertRaises(WebSocketDisconnect) as context, self.client.websocket_connect(
            "/ws/terminal/shell",
            headers={"host": "127.0.0.1", "origin": "https://evil.example"},
        ):
            pass
        self.assertEqual(context.exception.code, 1008)

    def test_real_forge_origin_is_accepted(self):
        with self.client.websocket_connect(
            "/ws/terminal/shell",
            headers={"host": "127.0.0.1", "origin": "http://127.0.0.1:5173"},
        ) as socket:
            self.assertIsNotNone(socket)

    def test_frontend_port_is_dynamic_without_wildcard_origins(self):
        with patch.dict(
            "os.environ",
            {"QUESTLAB_FRONTEND_PORT": "5275", "QUESTLAB_ALLOWED_ORIGINS": "tauri://localhost,*"},
            clear=False,
        ):
            origins = allowed_origins()
        self.assertEqual(origins[:2], ("http://127.0.0.1:5275", "http://localhost:5275"))
        self.assertIn("tauri://localhost", origins)
        self.assertNotIn("*", origins)

    def test_online_config_relay_returns_only_public_client_settings(self):
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"url": "https://example.supabase.co", "publishable_key": "sb_publishable_test"},
            )
        )
        original_client = httpx.AsyncClient
        with (
            patch.object(app_v2, "ONLINE_SERVICE_URL", "https://online.example"),
            patch.object(
                app_v2.httpx,
                "AsyncClient",
                side_effect=lambda *args, **kwargs: original_client(
                    *args, transport=transport, **kwargs
                ),
            ),
        ):
            response = self.client.get("/api/online/client-config")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertTrue(response.json()["publishable_key"].startswith("sb_publishable_"))

    def test_online_config_relay_rejects_secret_keys(self):
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"url": "https://example.supabase.co", "publishable_key": "sb_secret_test"},
            )
        )
        original_client = httpx.AsyncClient
        with patch.object(
            app_v2.httpx,
            "AsyncClient",
            side_effect=lambda *args, **kwargs: original_client(
                *args, transport=transport, **kwargs
            ),
        ):
            response = self.client.get("/api/online/client-config")
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
