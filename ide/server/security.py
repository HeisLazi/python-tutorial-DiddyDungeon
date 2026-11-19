"""Shared local-server security policy for Quest Lab.

The Forge backend is a loopback-only privileged service.  Browser origins are
matched exactly; there is deliberately no wildcard fallback.  A future Tauri
webview origin must be added explicitly through ``QUESTLAB_ALLOWED_ORIGINS``
after the packaging origin is verified (for example ``tauri://localhost`` or
``http://tauri.localhost``).  No Tauri origin is enabled by default.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

DEFAULT_FRONTEND_PORT = 5173
LOOPBACK_HOSTS = ("127.0.0.1", "localhost")


def frontend_port() -> int:
    """Return the validated Forge frontend port used for browser origins."""

    raw = os.getenv("QUESTLAB_FRONTEND_PORT", str(DEFAULT_FRONTEND_PORT)).strip()
    try:
        port = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_FRONTEND_PORT
    return port if 1 <= port <= 65535 else DEFAULT_FRONTEND_PORT


def _valid_explicit_origin(value: str) -> bool:
    if not value or "*" in value:
        return False
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https", "tauri"} or not parsed.netloc:
        return False
    return parsed.path in {"", "/"} and not parsed.params and not parsed.query and not parsed.fragment


def allowed_origins() -> tuple[str, ...]:
    """Return exact browser origins allowed to call the local backend.

    ``QUESTLAB_ALLOWED_ORIGINS`` is an explicit comma-separated extension for
    a verified desktop webview origin.  Invalid values and wildcards are
    ignored instead of weakening the default policy.
    """

    port = frontend_port()
    origins = [f"http://127.0.0.1:{port}", f"http://localhost:{port}"]
    for candidate in os.getenv("QUESTLAB_ALLOWED_ORIGINS", "").split(","):
        value = candidate.strip().rstrip("/")
        if _valid_explicit_origin(value) and value not in origins:
            origins.append(value)
    return tuple(origins)


def allowed_hosts() -> tuple[str, ...]:
    """Return the only Host names accepted by the loopback service."""

    return LOOPBACK_HOSTS


def is_allowed_origin(origin: str | None) -> bool:
    """Check a WebSocket Origin header using exact matching."""

    return bool(origin) and origin.strip().rstrip("/") in allowed_origins()

