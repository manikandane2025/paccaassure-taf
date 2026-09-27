"""RFC 9457 problem responses for every error (application/problem+json)."""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from northwind_api.models import FieldError, Problem

PROBLEM_MEDIA_TYPE = "application/problem+json"
PROBLEM_BASE = "https://api.northwind.example/problems/"
# 422 by value: the member name differs between Python 3.12 and 3.13.
UNPROCESSABLE = HTTPStatus(422)


class ProblemError(Exception):
    def __init__(
        self,
        status: HTTPStatus,
        detail: str,
        *,
        slug: str | None = None,
        errors: list[FieldError] | None = None,
        headers: dict[str, str] | None = None,
        existing_claim_id: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.problem = Problem(
            type=f"{PROBLEM_BASE}{slug}" if slug else "about:blank",
            title=status.phrase,
            status=status.value,
            detail=detail,
            errors=errors,
            existing_claim_id=existing_claim_id,
        )
        self.headers = headers


def problem_response(problem: Problem, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        problem.model_dump(mode="json", exclude_none=True),
        status_code=problem.status,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=headers,
    )


def field_errors(raw: list[Any]) -> list[FieldError]:
    return [
        FieldError(
            field=".".join(str(part) for part in error.get("loc", ())),
            message=str(error.get("msg", "")),
            type=str(error.get("type", "")),
        )
        for error in raw
    ]


# Standard responses for route docs, so the OpenAPI document shows the problem shape.
def problem_docs(*statuses: HTTPStatus) -> dict[int | str, dict[str, Any]]:
    return {
        status.value: {"model": Problem, "description": status.phrase, "content": {PROBLEM_MEDIA_TYPE: {}}}
        for status in statuses
    }


def install(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    def _api_problem(_: Request, exc: ProblemError) -> JSONResponse:
        return problem_response(exc.problem, exc.headers)

    @app.exception_handler(RequestValidationError)
    def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        status = UNPROCESSABLE
        problem = Problem(
            type=f"{PROBLEM_BASE}validation",
            title=status.phrase,
            status=status.value,
            detail="The request is invalid; see errors.",
            errors=field_errors(list(exc.errors())),
        )
        return problem_response(problem)

    @app.exception_handler(StarletteHTTPException)
    def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        status = HTTPStatus(exc.status_code)
        detail = exc.detail if isinstance(exc.detail, str) else status.description
        problem = Problem(title=status.phrase, status=status.value, detail=detail)
        return problem_response(problem, dict(exc.headers) if exc.headers else None)
