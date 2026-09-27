"""GET /health (public) and POST /admin/reset (role ADMIN)."""

from http import HTTPStatus

import pg8000.exceptions
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from northwind_api import VERSION
from northwind_api.db import Db, connect, one
from northwind_api.models import Health, ResetResult
from northwind_api.problems import problem_docs
from northwind_api.security import Admin

router = APIRouter(tags=["operations"])


@router.get(
    "/health",
    response_model=Health,
    responses={503: {"model": Health, "description": "Database unavailable"}},
)
def health() -> Health | JSONResponse:
    # Own connection (not the Db dependency): an unreachable database is a 503 body, not a 500.
    try:
        conn = connect()
        try:
            conn.run("SELECT 1")
        finally:
            conn.close()
    except (OSError, pg8000.exceptions.InterfaceError, pg8000.exceptions.DatabaseError):
        body = Health(status="degraded", database="unavailable", version=VERSION)
        return JSONResponse(body.model_dump(), status_code=HTTPStatus.SERVICE_UNAVAILABLE)
    return Health(status="ok", database="ok", version=VERSION)


@router.post(
    "/admin/reset",
    response_model=ResetResult,
    responses=problem_docs(HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN),
    summary="Restore the deterministic seed (role ADMIN)",
)
def reset(db: Db, _: Admin) -> ResetResult:
    db.run("SELECT nwh_reset_seed()")
    counts = one(
        db,
        "SELECT (SELECT count(*) FROM plans) AS plans, (SELECT count(*) FROM members) AS members,"
        " (SELECT count(*) FROM claims) AS claims",
    )
    if counts is None:
        raise RuntimeError("count query returned no row")
    return ResetResult(plans=counts["plans"], members=counts["members"], claims=counts["claims"])
