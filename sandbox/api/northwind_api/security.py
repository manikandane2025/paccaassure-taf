"""HMAC-signed bearer tokens and role checks.

Token = base64url(JSON payload) + "." + base64url(HMAC-SHA256). Deliberately simple: a sandbox for
testing auth providers (password and client_credentials grants, expiry, 401 vs 403), not a real IdP.
"""

import base64
import datetime as dt
import hashlib
import hmac
import json
from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from northwind_api.models import Principal, Role
from northwind_api.problems import ProblemError
from northwind_api.settings import get_settings

bearer = HTTPBearer(auto_error=False, description="Token from POST /auth/token.")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str) -> str:
    key = get_settings().token_secret.encode("utf-8")
    return _b64(hmac.new(key, payload.encode("ascii"), hashlib.sha256).digest())


def issue(principal: Principal) -> str:
    body = {
        "sub": principal.subject,
        "name": principal.display_name,
        "role": principal.role.value,
        "kind": principal.kind,
        "exp": int(principal.expires_at.timestamp()),
    }
    payload = _b64(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    return f"{payload}.{_sign(payload)}"


def _unauthorized(detail: str, error: str = "invalid_token") -> ProblemError:
    challenge = f'Bearer realm="northwind", error="{error}", error_description="{detail}"'
    return ProblemError(
        HTTPStatus.UNAUTHORIZED, detail, slug="unauthorized", headers={"WWW-Authenticate": challenge}
    )


def verify(token: str, now: dt.datetime | None = None) -> Principal:
    payload, _, signature = token.partition(".")
    if not payload or not signature or not hmac.compare_digest(signature, _sign(payload)):
        raise _unauthorized("The access token is invalid.")
    try:
        body = json.loads(_unb64(payload))
        expires_at = dt.datetime.fromtimestamp(int(body["exp"]), tz=dt.UTC)
        principal = Principal(
            subject=body["sub"],
            display_name=body["name"],
            role=Role(body["role"]),
            kind=body["kind"],
            expires_at=expires_at,
        )
    except (ValueError, KeyError, TypeError) as error:
        raise _unauthorized("The access token is invalid.") from error
    if (now or dt.datetime.now(dt.UTC)) >= principal.expires_at:
        raise _unauthorized("The access token expired.")
    return principal


def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    if credentials is None:
        raise ProblemError(
            HTTPStatus.UNAUTHORIZED,
            "Authentication required: send Authorization: Bearer <token>.",
            slug="unauthorized",
            headers={"WWW-Authenticate": 'Bearer realm="northwind"'},
        )
    return verify(credentials.credentials)


CurrentPrincipal = Annotated[Principal, Depends(current_principal)]


def require(*roles: Role) -> Callable[[Principal], Principal]:
    allowed = frozenset(roles)

    def check(principal: CurrentPrincipal) -> Principal:
        if principal.role not in allowed:
            names = ", ".join(sorted(role.value for role in allowed))
            raise ProblemError(
                HTTPStatus.FORBIDDEN, f"Role {principal.role.value} may not do this (needs {names}).",
                slug="forbidden",
            )  # fmt: skip
        return principal

    return check


Editor = Annotated[Principal, Depends(require(Role.ADMIN, Role.EXAMINER))]
Admin = Annotated[Principal, Depends(require(Role.ADMIN))]
