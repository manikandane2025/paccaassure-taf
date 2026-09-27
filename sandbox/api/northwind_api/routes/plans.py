"""GET /plans and GET /plans/{plan_code}: public (no token), for unauthenticated-endpoint tests."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Path, Query

from northwind_api.db import Db, one, rows
from northwind_api.models import Plan, PlanCode
from northwind_api.problems import ProblemError, problem_docs

router = APIRouter(prefix="/plans", tags=["plans"])

PLAN_COLUMNS = "plan_code, name, tier, monthly_premium, deductible, active, description"


@router.get("", response_model=list[Plan], summary="List plans")
def list_plans(
    db: Db, active: Annotated[bool | None, Query(description="Filter by active flag.")] = None
) -> list[Plan]:
    found = rows(
        db,
        f"SELECT {PLAN_COLUMNS} FROM plans"  # noqa: S608 - fixed column list; values are bound
        " WHERE CAST(:active AS boolean) IS NULL OR active = CAST(:active AS boolean) ORDER BY plan_code",
        active=active,
    )
    return [Plan.model_validate(row) for row in found]


@router.get("/{plan_code}", response_model=Plan, responses=problem_docs(HTTPStatus.NOT_FOUND))
def get_plan(db: Db, plan_code: Annotated[PlanCode, Path()]) -> Plan:
    row = one(db, f"SELECT {PLAN_COLUMNS} FROM plans WHERE plan_code = :code", code=plan_code)  # noqa: S608
    if row is None:
        raise ProblemError(HTTPStatus.NOT_FOUND, f"Plan {plan_code} does not exist.", slug="not-found")
    return Plan.model_validate(row)
