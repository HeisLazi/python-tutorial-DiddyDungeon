"""Trusted server-only gateway for idempotent group ladder settlement.

The secret is read from the host's secret manager at runtime, never from a
player or the match database. The database function grants execution only to
the service role. Match records and the outbox are created by the coordinator.
"""
from __future__ import annotations

from urllib.parse import urlsplit
import httpx


class SettlementUnavailable(RuntimeError):
    pass


class RankedSettlementClient:
    def __init__(self, supabase_url: str, secret: str, *, client: httpx.AsyncClient | None = None):
        url = urlsplit(supabase_url)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise SettlementUnavailable('The ranked settlement service requires HTTPS.')
        if not isinstance(secret, str) or len(secret) < 32:
            raise SettlementUnavailable('The ranked settlement credential is unavailable.')
        self._url = supabase_url.rstrip('/')
        self._secret = secret
        self._client = client

    async def settle(self, result: dict) -> None:
        allowed = {'match_id', 'target_group', 'first_player', 'second_player', 'winning_player'}
        if not isinstance(result, dict) or set(result) != allowed:
            raise SettlementUnavailable('Invalid ranked result.')
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=4.0), follow_redirects=False)
        try:
            response = await client.post(self._url + '/rest/v1/rpc/settle_hunter_ranked_match',
                                         headers={'apikey':self._secret}, json=result)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # A failed or ambiguous request stays in the durable outbox. The
            # database function checks idempotency before applying any rating.
            raise SettlementUnavailable('Ranked settlement is unavailable.') from exc
        finally:
            if owns_client:
                await client.aclose()
