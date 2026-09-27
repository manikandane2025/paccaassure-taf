"""POST /auth/token (password and client_credentials grants) and GET /auth/me."""

import datetime as dt
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body

from northwind_api.db import Db, one
from northwind_api.models import (
    ClientCredentialsGrant,
    PasswordGrant,
    Principal,
    Role,
    Token,
    TokenRequest,
)
from northwind_api.problems import ProblemError, problem_docs
from northwind_api.security import CurrentPrincipal, issue
from northwind_api.settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _invalid_grant(detail: str) -> ProblemError:
    return ProblemError(HTTPStatus.UNAUTHORIZED, detail, slug="invalid-grant")


@router.post(
    "/token",
    response_model=Token,
    responses=problem_docs(HTTPStatus.UNAUTHORIZED, HTTPStatus(422), HTTPStatus.LOCKED),
    summary="Exchange credentials for a bearer token",
)
def token(db: Db, grant: Annotated[TokenRequest, Body()]) -> Token:
    ttl = get_settings().token_ttl_seconds
    expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=ttl)
    if isinstance(grant, PasswordGrant):
        user = one(
            db,
            "SELECT username, display_name, role, locked, password_hash = crypt(:pw, password_hash) AS ok"
            " FROM app_users WHERE username = :username",
            username=grant.username,
            pw=grant.password,
        )
        if user is None or not user["ok"]:
            raise _invalid_grant("Invalid username or password.")
        if user["locked"]:
            raise ProblemError(HTTPStatus.LOCKED, "This account is locked.", slug="account-locked")
        principal = Principal(
            subject=user["username"],
            display_name=user["display_name"],
            role=Role(user["role"]),
            kind="user",
            expires_at=expires_at,
        )
    else:
        client = _client(db, grant)
        principal = Principal(
            subject=client["client_id"],
            display_name=client["client_id"],
            role=Role(client["role"]),
            kind="client",
            expires_at=expires_at,
        )
    return Token(
        access_token=issue(principal),
        expires_in=ttl,
        role=principal.role,
        display_name=principal.display_name,
    )


def _client(db: Db, grant: ClientCredentialsGrant) -> dict[str, str]:
    client = one(
        db,
        "SELECT client_id, role, secret_hash = crypt(:secret, secret_hash) AS ok"
        " FROM api_clients WHERE client_id = :client_id",
        client_id=grant.client_id,
        secret=grant.client_secret,
    )
    if client is None or not client["ok"]:
        raise _invalid_grant("Invalid client credentials.")
    return {"client_id": client["client_id"], "role": client["role"]}


@router.get("/me", response_model=Principal, responses=problem_docs(HTTPStatus.UNAUTHORIZED))
def me(principal: CurrentPrincipal) -> Principal:
    return principal
