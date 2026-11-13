"""Internal-only isolated evaluator API.

Run on a dedicated gVisor-capable host behind authenticated HTTPS. The Docker
socket belongs only to this worker, never to the match server or a sandbox.
It cannot serve files, save data, or arbitrary commands.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import hmac
import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .sandbox import Sandbox, SandboxUnavailable
from ..content_revision import WORKER_REVISION

SECRET = os.environ.get('QUESTLAB_WORKER_SECRET', '')
IMAGE_ID = os.environ.get('QUESTLAB_WORKER_IMAGE_ID', '')
worker: Sandbox | None = None


@asynccontextmanager
async def lifespan(_app):
    global worker
    try:
        if len(SECRET) < 32 or not SECRET.isascii():
            raise SandboxUnavailable('Worker credential unavailable.')
        candidate = Sandbox(IMAGE_ID)
        await candidate.check_runtime()
        worker = candidate
    except (OSError, SandboxUnavailable):
        worker = None
    yield
    worker = None


app = FastAPI(title='Quest Lab isolated evaluation worker', lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


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


class EvaluationRequest(BaseModel):
    challenge_id: str = Field(max_length=64)
    evaluation_id: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=20000)
    revision: str = Field(min_length=64, max_length=64)


class PracticeRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=20000)
    stdin: str = Field(default='', max_length=4000)


def authorized(authorization: str) -> None:
    scheme, _, token = authorization.partition(' ')
    if len(SECRET) < 32 or not SECRET.isascii() or not token.isascii() or scheme.lower() != 'bearer' or not hmac.compare_digest(token, SECRET):
        raise HTTPException(status_code=401, detail='Unauthorized.')


@app.post('/evaluate')
async def evaluate(payload: EvaluationRequest, authorization: str = Header(default='')):
    authorized(authorization)
    if not payload.revision.isascii() or not hmac.compare_digest(payload.revision, WORKER_REVISION):
        raise HTTPException(status_code=503, detail='The isolated evaluator is unavailable.')
    if worker is None:
        raise HTTPException(status_code=503, detail='The isolated evaluator is unavailable.')
    try:
        passed = await worker.evaluate(payload.challenge_id, payload.source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail='Invalid evaluation request.') from exc
    except (OSError, SandboxUnavailable) as exc:
        raise HTTPException(status_code=503, detail='The isolated evaluator is unavailable.') from exc
    return {'evaluation_id': payload.evaluation_id, 'passed': passed, 'revision': WORKER_REVISION}


@app.post('/practice')
async def practice(payload: PracticeRequest, authorization: str = Header(default='')):
    authorized(authorization)
    if worker is None:
        raise HTTPException(status_code=503, detail='The isolated evaluator is unavailable.')
    try:
        result = await worker.practice(payload.source, payload.stdin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail='Invalid practice request.') from exc
    except (OSError, SandboxUnavailable) as exc:
        raise HTTPException(status_code=503, detail='The isolated evaluator is unavailable.') from exc
    return {'request_id': payload.request_id, **result}
