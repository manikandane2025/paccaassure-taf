"""FastAPI application: routers, problem handlers, ``delay_ms`` and ``X-Request-ID`` on every call.

Run: uvicorn northwind_api.app:app --host 0.0.0.0 --port 8000
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request, Response

from northwind_api import VERSION, problems
from northwind_api.routes import auth, claims, members, ops, plans
from northwind_api.settings import get_settings

DESCRIPTION = """\
Northwind Health sandbox API: a **fictitious** company with **synthetic** data, for PaccaAssureTAF e2e
scenarios. Never use real data here.

* Auth: `POST /auth/token` (password or client_credentials grant), then `Authorization: Bearer <token>`.
* Errors: RFC 9457 `application/problem+json` with `errors[]` for field problems.
* Every operation accepts `delay_ms` (0-30000) to simulate a slow backend, and echoes `X-Request-ID`.
* `POST /admin/reset` restores the deterministic seed.
"""


async def simulated_delay(
    delay_ms: Annotated[
        int, Query(ge=0, le=30_000, description="Delay the response by this many ms (wait/timeout tests).")
    ] = 0,
) -> None:
    if delay_ms:
        # Server-side latency simulation for the framework's wait tests (not test code: hard rule 5
        # bans sleeps in scripts and the framework, not in the sandbox app under test).
        await asyncio.sleep(min(delay_ms, get_settings().max_delay_ms) / 1000)  # noqa: TID251


def create_app() -> FastAPI:
    app = FastAPI(
        title="Northwind Health API",
        version=VERSION,
        description=DESCRIPTION,
        dependencies=[Depends(simulated_delay)],
    )
    problems.install(app)

    @app.middleware("http")
    async def request_id(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        value = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = value
        return response

    for module in (ops, auth, plans, members, claims):
        app.include_router(module.router)
    return app


app = create_app()
