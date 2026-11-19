"""Dedicated online duel API; no access to Quest Lab's local game server.

Set QUESTLAB_ONLINE_SUPABASE_URL, QUESTLAB_ONLINE_SUPABASE_PUBLISHABLE_KEY,
QUESTLAB_ONLINE_EVALUATOR_URL and QUESTLAB_ONLINE_EVALUATOR_SECRET in the host
runtime. The evaluator URL may be HTTPS or an absolute unix:/// socket in a
private directory. Configure QUESTLAB_ONLINE_ALLOWED_ORIGINS as exact comma-separated
HTTPS or Tauri origins. No credentials are persisted or logged here.

An optional dedicated QUESTLAB_ONLINE_MATCH_DB SQLite file makes matches
recoverable and owns the idempotent, group-scoped ranked ladder. It is separate
from campaign saves and does not need a database service-role credential.
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .coordinator import DuelCoordinator
from .duel import DuelError
from .evaluator import EvaluatorUnavailable, IsolatedEvaluator
from .loadouts import public_catalog
from .ownership import RANKED_GEAR
from .raid import RaidCoordinator
from .repository import MatchRepository, MatchStoreError
from .shop import ONLINE_MASTERY_BY_ID


def _https_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return ''
    return value.rstrip('/')


SUPABASE_URL = _https_url(os.environ.get('QUESTLAB_ONLINE_SUPABASE_URL', ''))
PUBLISHABLE_KEY = os.environ.get('QUESTLAB_ONLINE_SUPABASE_PUBLISHABLE_KEY', '')
EVALUATOR_URL = os.environ.get('QUESTLAB_ONLINE_EVALUATOR_URL', '')
EVALUATOR_SECRET = os.environ.get('QUESTLAB_ONLINE_EVALUATOR_SECRET', '')
try:
    evaluator = IsolatedEvaluator(EVALUATOR_URL, EVALUATOR_SECRET)
except EvaluatorUnavailable:
    evaluator = None
database_path = os.environ.get('QUESTLAB_ONLINE_MATCH_DB', '').strip()
repository = MatchRepository(database_path) if database_path else None
coordinator = DuelCoordinator(evaluator, repository=repository)
raid_coordinator = RaidCoordinator(evaluator, repository) if repository else None


def _mastery_progress(user_id: str) -> dict:
    lookup = getattr(repository, 'online_mastery_progress', None)
    if not callable(lookup):
        return {'total_wins':0, 'weapon_wins':{}, 'owned_ids':[]}
    return lookup(user_id)


class LocalRankedSettlement:
    """Apply verified match results to the private host's durable ladder."""
    def __init__(self, store: MatchRepository):
        self.store = store

    async def settle(self, result: dict) -> None:
        self.store.settle_ranked_result(result)


settler = LocalRankedSettlement(repository) if repository else None


@asynccontextmanager
async def lifespan(_app):
    async def settle_loop():
        while True:
            try:
                await coordinator.expire_inactive()
                await coordinator.flush_settlements(settler)
            except MatchStoreError:
                return  # Fail closed; an operator must repair the store.
            await asyncio.sleep(5)
    task = asyncio.create_task(settle_loop()) if settler is not None else None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if repository is not None:
            repository.close()


app = FastAPI(title='Quest Lab online duel service', docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


@app.exception_handler(MatchStoreError)
async def match_storage_error(_request, _error):
    return JSONResponse(status_code=503, content={'detail':'Online match storage is unavailable.'})
origins = [s.strip() for s in os.environ.get('QUESTLAB_ONLINE_ALLOWED_ORIGINS', '').split(',') if s.strip()]
if any(origin == '*' or origin.endswith('/') or not urlsplit(origin).scheme or not urlsplit(origin).netloc or urlsplit(origin).path or urlsplit(origin).query or urlsplit(origin).fragment for origin in origins):
    raise RuntimeError('Online CORS origins must be explicit origins.')
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=['GET', 'POST'], allow_headers=['authorization', 'content-type'])


@app.middleware('http')
async def bound_request_size(request, call_next):
    if request.method == 'POST':
        try:
            size = int(request.headers.get('content-length', ''))
        except ValueError:
            return JSONResponse(status_code=411, content={'detail':'A bounded request is required.'})
        if size < 0 or size > 160000:
            return JSONResponse(status_code=413, content={'detail':'Request is too large.'})
    return await call_next(request)


def uid(value: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail='Invalid identifier.') from exc


def raid_uid(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 64 or not value.replace('-', '').replace('_', '').isalnum():
        raise HTTPException(status_code=400, detail='Invalid project identifier.')
    return value


async def bearer(authorization: str = Header(default='')) -> str:
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token or len(token) > 8192:
        raise HTTPException(status_code=401, detail='Sign in first.')
    if not SUPABASE_URL or not PUBLISHABLE_KEY:
        raise HTTPException(status_code=503, detail='Account service is not configured.')
    return token


async def authorize_group(group_id: str, token: str, other_id: str = '') -> str:
    """Ask Auth to validate the JWT and use its RLS-filtered membership rows."""
    group_id = uid(group_id)
    headers = {'apikey': PUBLISHABLE_KEY, 'Authorization': f'Bearer {token}'}
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
            user = await client.get(SUPABASE_URL + '/auth/v1/user', headers=headers)
            if user.status_code in (401, 403):
                raise HTTPException(status_code=401, detail='Your session has expired. Sign in again.')
            user.raise_for_status()
            player_id = uid(user.json().get('id', ''))
            rows = await client.get(SUPABASE_URL + '/rest/v1/hunter_group_members', headers=headers,
                                    params={'select': 'user_id', 'group_id': 'eq.' + group_id})
            rows.raise_for_status()
            data = rows.json()
            if not isinstance(data, list):
                raise ValueError('Invalid membership response')
            members = {str(row.get('user_id')) for row in data if isinstance(row, dict)}
            if player_id not in members or (other_id and uid(other_id) not in members):
                raise HTTPException(status_code=403, detail='You and your opponent must belong to this group.')
            return player_id
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail='Group authorization is unavailable.') from exc


async def authorize_group_members(group_id: str, token: str) -> tuple[str, list[str]]:
    """Return the caller and RLS-filtered roster for a private group operation."""
    group_id = uid(group_id)
    player_id = await authorize_group(group_id, token)
    headers = {'apikey': PUBLISHABLE_KEY, 'Authorization': f'Bearer {token}'}
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
            rows = await client.get(SUPABASE_URL + '/rest/v1/hunter_group_members', headers=headers,
                                    params={'select':'user_id', 'group_id':'eq.' + group_id})
            rows.raise_for_status()
            data = rows.json()
            if not isinstance(data, list) or len(data) > 4 or any(not isinstance(row, dict) for row in data):
                raise ValueError('Invalid group roster')
            members = sorted({uid(row.get('user_id', '')) for row in data})
            if player_id not in members:
                raise HTTPException(status_code=403, detail='You must belong to this group.')
            return player_id, members
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail='Group authorization is unavailable.') from exc


async def verified_gear(player_id: str, token: str) -> frozenset[str]:
    """Read only the already-authenticated player's server-issued gear rows."""
    player_id = uid(player_id)
    if not SUPABASE_URL or not PUBLISHABLE_KEY:
        raise HTTPException(status_code=503, detail='Verified gear is unavailable.')
    headers = {'apikey': PUBLISHABLE_KEY, 'Authorization': f'Bearer {token}'}
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
            response = await client.get(SUPABASE_URL + '/rest/v1/verified_hunter_gear', headers=headers,
                                        params={'select':'item_id', 'user_id':'eq.' + player_id})
            response.raise_for_status()
            rows = response.json()
            if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get('item_id'), str) for row in rows):
                raise ValueError('Invalid ownership response')
            return frozenset(row['item_id'] for row in rows)
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail='Verified gear is unavailable.') from exc


class InviteRequest(BaseModel):
    guest_id: str = Field(max_length=36)
    chain_id: str = Field(max_length=32)
    mode: str = Field(default='fair', max_length=16)


class LoadoutRequest(BaseModel):
    weapon: str | None = Field(default=None, max_length=128)
    armor: str | None = Field(default=None, max_length=128)
    trinket: str | None = Field(default=None, max_length=128)
    weapon_appearance: str | None = Field(default=None, max_length=128)
    armor_appearance: str | None = Field(default=None, max_length=128)


class SubmissionRequest(BaseModel):
    stance: str = Field(max_length=12)
    code: str = Field(default='', max_length=20000)
    choice: int | None = Field(default=None, ge=0, le=9)


class PracticeRequest(BaseModel):
    code: str = Field(max_length=20000)
    stdin: str = Field(default='', max_length=4000)


class BonusRequest(BaseModel):
    answer: int = Field(strict=True, ge=0, le=2)
    reward: str = Field(max_length=8)


class RaidAssignRequest(BaseModel):
    task_id: str = Field(max_length=40)
    target_id: str = Field(max_length=36)


class RaidTaskRequest(BaseModel):
    task_id: str = Field(max_length=40)


class RaidTaskSwapRequest(BaseModel):
    task_id: str = Field(max_length=40)
    other_task_id: str = Field(max_length=40)


class RaidSubmissionRequest(BaseModel):
    task_id: str = Field(max_length=40)
    request_id: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=1, max_length=20000)


class RaidReviewRequest(BaseModel):
    task_id: str = Field(max_length=40)
    decision: str = Field(max_length=24)


class RaidBossSubmissionRequest(BaseModel):
    question_id: str = Field(max_length=40)
    request_id: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=1, max_length=20000)


class RaidBossFeintRequest(BaseModel):
    decision: str = Field(max_length=16)


class MerchantPurchaseRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=128)


def problem(exc: Exception) -> HTTPException:
    if isinstance(exc, EvaluatorUnavailable):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, DuelError) and str(exc).endswith('not found.'):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@app.get('/health')
async def health():
    return {'ok': not coordinator.storage_failed and not (raid_coordinator and raid_coordinator.storage_failed), 'accounts_configured': bool(SUPABASE_URL and PUBLISHABLE_KEY),
            'evaluator_configured': evaluator is not None, 'durable_matches': repository is not None and not coordinator.storage_failed,
            'settlement_configured': settler is not None, 'ranked_enabled': settler is not None and not coordinator.storage_failed,
            'merchant_configured': bool(SUPABASE_URL and PUBLISHABLE_KEY and repository is not None and not coordinator.storage_failed),
            'cooperative_projects': raid_coordinator is not None and not raid_coordinator.storage_failed}


@app.get('/client-config')
async def client_config():
    # Only the explicitly public modern key is suitable for browser clients.
    # Never expose a legacy JWT, secret key, or worker/settlement credential.
    if not SUPABASE_URL or not PUBLISHABLE_KEY.startswith('sb_publishable_'):
        raise HTTPException(status_code=503, detail='Account configuration is unavailable.')
    return JSONResponse({'url':SUPABASE_URL, 'publishable_key':PUBLISHABLE_KEY},
                        headers={'Cache-Control':'no-store'})


@app.post('/groups/{group_id}/invites')
async def invite(group_id: str, payload: InviteRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token, payload.guest_id)
    try:
        return await coordinator.invite(uid(group_id), player, uid(payload.guest_id), payload.chain_id, payload.mode)
    except (DuelError, EvaluatorUnavailable) as exc:
        raise problem(exc) from exc


@app.get('/groups/{group_id}/invites')
async def pending(group_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    return {'invitations': await coordinator.pending_for(uid(group_id), player)}


@app.get('/groups/{group_id}/invites/{invite_id}')
async def invitation(group_id: str, invite_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    try:
        return await coordinator.invitation_status(uid(group_id), player, invite_id)
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/invites/{invite_id}/accept')
async def accept(group_id: str, invite_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    try:
        pending_invites = await coordinator.pending_for(uid(group_id), player)
        original = next((item for item in pending_invites if item['invite_id'] == invite_id), None)
        if original:
            await authorize_group(group_id, token, original['host_id'])
        return await coordinator.accept(uid(group_id), player, invite_id)
    except (DuelError, EvaluatorUnavailable) as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/invites/{invite_id}/withdraw')
async def withdraw(group_id: str, invite_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    try:
        await coordinator.withdraw(uid(group_id), player, invite_id)
        return {'withdrawn': True}
    except DuelError as exc:
        raise problem(exc) from exc


@app.get('/groups/{group_id}/matches/recoverable')
async def recoverable_matches(group_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    try:
        return {'matches': await coordinator.recoverable_for(uid(group_id), player)}
    except DuelError as exc:
        raise problem(exc) from exc


@app.get('/groups/{group_id}/matches/{match_id}')
async def match(group_id: str, match_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    try:
        return await coordinator.view(uid(group_id), player, match_id)
    except DuelError as exc:
        raise problem(exc) from exc


@app.get('/groups/{group_id}/loadouts')
async def loadout_catalog(group_id: str, mode: str = 'fair', token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if mode not in ('fair', 'friendly', 'geared'):
        raise HTTPException(status_code=400, detail='Choose a valid duel mode.')
    catalog = public_catalog()
    owned_ids = []
    if mode == 'geared':
        if settler is None:
            raise HTTPException(status_code=503, detail='Ranked duels are unavailable until durable ladder storage is configured.')
        local_online = repository.online_owned_items(uid(group_id), player) if repository is not None else []
        verified = await verified_gear(player, token)
        owned_ids = sorted((verified | frozenset(local_online)) & RANKED_GEAR)
        allowed = set(owned_ids)
        catalog = {slot: [item for item in items if item['id'] in allowed] for slot, items in catalog.items()}
    mastery = _mastery_progress(player)
    return {'catalog': catalog, 'owned_ids': owned_ids,
            'appearances': [dict(item) for item in ONLINE_MASTERY_BY_ID.values()],
            'owned_appearance_ids': mastery['owned_ids'],
            'mastery_progress': {'total_wins':mastery.get('total_wins', 0),
                                 'weapon_wins':mastery.get('weapon_wins', {})},
            'modes': ['fair', 'friendly', 'geared'] if settler else ['fair', 'friendly']}


@app.get('/groups/{group_id}/ladder')
async def group_ladder(group_id: str, token: str = Depends(bearer)):
    await authorize_group(group_id, token)
    if repository is None or coordinator.storage_failed:
        raise HTTPException(status_code=503, detail='The private group ladder is unavailable.')
    return {'ratings': repository.group_ratings(uid(group_id))}


@app.get('/groups/{group_id}/wallet')
async def group_wallet(group_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if repository is None or coordinator.storage_failed:
        raise HTTPException(status_code=503, detail='The online wallet is unavailable.')
    return repository.online_wallet(uid(group_id), player)


@app.get('/groups/{group_id}/merchant')
async def group_merchant(group_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if repository is None or coordinator.storage_failed:
        raise HTTPException(status_code=503, detail='The online merchant is unavailable.')
    group_id = uid(group_id)
    return {'available':False,
            'catalog':[],
            'owned_ids':repository.online_owned_items(group_id, player),
            'owned_appearance_ids':_mastery_progress(player)['owned_ids'],
            'mastery_progress':_mastery_progress(player),
            'wallet':repository.online_wallet(group_id, player)}


@app.post('/groups/{group_id}/merchant/purchase')
async def purchase_online_item(group_id: str, request: MerchantPurchaseRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if repository is None or coordinator.storage_failed:
        raise HTTPException(status_code=503, detail='The online merchant is unavailable.')
    raise HTTPException(status_code=503, detail='Sir Getrich’s shop is coming soon. Wazi Bucks are still earned for Colosseum wins.')


@app.post('/groups/{group_id}/raids')
async def create_raid(group_id: str, token: str = Depends(bearer)):
    player, members = await authorize_group_members(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    try:
        return await raid_coordinator.create(uid(group_id), player, members)
    except DuelError as exc:
        raise problem(exc) from exc


@app.get('/groups/{group_id}/raids/active')
async def active_raid(group_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    return {'raid':await raid_coordinator.current(uid(group_id), player)}


@app.get('/groups/{group_id}/raids/{raid_id}')
async def get_raid(group_id: str, raid_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    try:
        return await raid_coordinator.view(uid(group_id), player, raid_uid(raid_id))
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/raids/{raid_id}/assign')
async def assign_raid_task(group_id: str, raid_id: str, payload: RaidAssignRequest, token: str = Depends(bearer)):
    player, current_members = await authorize_group_members(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    target = uid(payload.target_id)
    if target not in current_members:
        raise HTTPException(status_code=403, detail='Assign work to a current member of this group.')
    try:
        return await raid_coordinator.assign(uid(group_id), player, raid_uid(raid_id), payload.task_id, target)
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/raids/{raid_id}/volunteer/open')
async def open_raid_task_for_volunteers(group_id: str, raid_id: str, payload: RaidTaskRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    try:
        return await raid_coordinator.open_for_volunteers(uid(group_id), player, raid_uid(raid_id), payload.task_id)
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/raids/{raid_id}/volunteer/claim')
async def volunteer_for_raid_task(group_id: str, raid_id: str, payload: RaidTaskRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    try:
        return await raid_coordinator.volunteer(uid(group_id), player, raid_uid(raid_id), payload.task_id)
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/raids/{raid_id}/swap')
async def swap_raid_tasks(group_id: str, raid_id: str, payload: RaidTaskSwapRequest, token: str = Depends(bearer)):
    player, current_members = await authorize_group_members(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    try:
        return await raid_coordinator.swap(uid(group_id), player, raid_uid(raid_id), payload.task_id,
                                           payload.other_task_id, current_members)
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/raids/{raid_id}/submit')
async def submit_raid_task(group_id: str, raid_id: str, payload: RaidSubmissionRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    try:
        return await raid_coordinator.submit(uid(group_id), player, raid_uid(raid_id), payload.task_id,
                                             payload.request_id, payload.code)
    except (DuelError, EvaluatorUnavailable) as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/raids/{raid_id}/review')
async def review_raid_task(group_id: str, raid_id: str, payload: RaidReviewRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    try:
        return await raid_coordinator.review(uid(group_id), player, raid_uid(raid_id), payload.task_id, payload.decision)
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/raids/{raid_id}/abandon')
async def abandon_raid(group_id: str, raid_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    try:
        return await raid_coordinator.abandon(uid(group_id), player, raid_uid(raid_id))
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/raids/{raid_id}/boss/start')
async def start_raid_boss(group_id: str, raid_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    try:
        return await raid_coordinator.start_boss(uid(group_id), player, raid_uid(raid_id))
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/raids/{raid_id}/boss/submit')
async def submit_raid_boss(group_id: str, raid_id: str, payload: RaidBossSubmissionRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    try:
        return await raid_coordinator.submit_boss(uid(group_id), player, raid_uid(raid_id), payload.question_id,
                                                  payload.request_id, payload.code)
    except (DuelError, EvaluatorUnavailable) as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/raids/{raid_id}/boss/feint')
async def resolve_raid_boss_feint(group_id: str, raid_id: str, payload: RaidBossFeintRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    if raid_coordinator is None:
        raise HTTPException(status_code=503, detail='Cooperative projects are unavailable until durable online storage is configured.')
    try:
        return await raid_coordinator.resolve_boss_feint(uid(group_id), player, raid_uid(raid_id), payload.decision)
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/matches/{match_id}/loadout')
async def loadout(group_id: str, match_id: str, payload: LoadoutRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    try:
        current = await coordinator.view(uid(group_id), player, match_id)
        mastery_owned = frozenset(_mastery_progress(player)['owned_ids'])
        if current.get('mode') == 'geared':
            owned = await verified_gear(player, token)
            if repository is not None:
                owned = owned | frozenset(repository.online_owned_items(uid(group_id), player))
        else:
            owned = None
        return await coordinator.loadout(uid(group_id), player, match_id, payload.model_dump(),
                                         verified_ids=owned, mastery_owned_ids=mastery_owned)
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/matches/{match_id}/submit')
async def submit(group_id: str, match_id: str, payload: SubmissionRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    try:
        return await coordinator.submit(uid(group_id), player, match_id, payload.stance, payload.code, payload.choice)
    except (DuelError, EvaluatorUnavailable) as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/matches/{match_id}/practice')
async def practice(group_id: str, match_id: str, payload: PracticeRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    try:
        return await coordinator.practice(uid(group_id), player, match_id, payload.code, payload.stdin)
    except (DuelError, EvaluatorUnavailable) as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/matches/{match_id}/bonus')
async def bonus(group_id: str, match_id: str, payload: BonusRequest, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    try:
        return await coordinator.bonus(uid(group_id), player, match_id, payload.answer, payload.reward)
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/matches/{match_id}/ready')
async def ready(group_id: str, match_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    try:
        return await coordinator.ready(uid(group_id), player, match_id)
    except DuelError as exc:
        raise problem(exc) from exc


@app.post('/groups/{group_id}/matches/{match_id}/cancel')
async def cancel(group_id: str, match_id: str, token: str = Depends(bearer)):
    player = await authorize_group(group_id, token)
    try:
        return await coordinator.cancel(uid(group_id), player, match_id)
    except DuelError as exc:
        raise problem(exc) from exc
