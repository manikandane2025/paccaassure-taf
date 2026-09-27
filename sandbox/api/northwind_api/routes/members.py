"""Members: search with filters and paging, CSV export, detail, update (409 on stale version)."""

import csv
import datetime as dt
import io
import math
from dataclasses import dataclass
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import Response

from northwind_api.db import Db, Row, one, rows
from northwind_api.models import (
    Claim,
    Member,
    MemberId,
    MemberPage,
    MemberSort,
    MemberStatus,
    MemberUpdate,
    PlanCode,
)
from northwind_api.problems import UNPROCESSABLE, ProblemError, problem_docs
from northwind_api.routes.claims import CLAIM_COLUMNS
from northwind_api.security import CurrentPrincipal, Editor

router = APIRouter(prefix="/members", tags=["members"])

MEMBER_COLUMNS = (
    "member_id, first_name, last_name, date_of_birth, ssn, email, phone, address_line, city, state,"
    " postal_code, status, plan_code, enrolled_on, version, updated_at"
)
EXPORT_COLUMNS = (
    "member_id", "first_name", "last_name", "date_of_birth", "status", "plan_code", "state", "email",
)  # fmt: skip
EXPORT_LIMIT = 1000
ORDER_BY: dict[MemberSort, str] = {
    MemberSort.LAST_NAME: "lower(last_name), lower(first_name), member_id",
    MemberSort.MEMBER_ID: "member_id",
    MemberSort.DATE_OF_BIRTH: "date_of_birth, member_id",
}


@dataclass(frozen=True)
class MemberFilters:
    member_id: Annotated[str | None, Query(description="Exact member id, e.g. NWH-M000123.")] = None
    last_name: Annotated[str | None, Query(max_length=40, description="Case-insensitive prefix.")] = None
    first_name: Annotated[str | None, Query(max_length=40, description="Case-insensitive prefix.")] = None
    date_of_birth: Annotated[dt.date | None, Query()] = None
    status: Annotated[MemberStatus | None, Query()] = None
    plan_code: Annotated[PlanCode | None, Query()] = None
    state: Annotated[str | None, Query(pattern=r"^[A-Z]{2}$")] = None

    def where(self) -> tuple[str, dict[str, object]]:
        # Fixed SQL fragments only; every value is a bound parameter.
        clauses: list[str] = []
        params: dict[str, object] = {}
        if self.member_id:
            clauses.append("member_id = :member_id")
            params["member_id"] = self.member_id.strip().upper()
        if self.last_name:
            clauses.append("lower(last_name) LIKE :last_name")
            params["last_name"] = _prefix(self.last_name)
        if self.first_name:
            clauses.append("lower(first_name) LIKE :first_name")
            params["first_name"] = _prefix(self.first_name)
        if self.date_of_birth:
            clauses.append("date_of_birth = :date_of_birth")
            params["date_of_birth"] = self.date_of_birth
        if self.status:
            clauses.append("status = :status")
            params["status"] = self.status.value
        if self.plan_code:
            clauses.append("plan_code = :plan_code")
            params["plan_code"] = self.plan_code
        if self.state:
            clauses.append("state = :state")
            params["state"] = self.state
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def _prefix(text: str) -> str:
    escaped = text.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"{escaped}%"


Filters = Annotated[MemberFilters, Depends()]


def _not_found(member_id: str) -> ProblemError:
    return ProblemError(HTTPStatus.NOT_FOUND, f"Member {member_id} does not exist.", slug="not-found")


@router.get("", response_model=MemberPage, responses=problem_docs(HTTPStatus.UNAUTHORIZED, UNPROCESSABLE))
def search_members(
    db: Db,
    _: CurrentPrincipal,
    filters: Filters,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: MemberSort = MemberSort.LAST_NAME,
) -> MemberPage:
    where, params = filters.where()
    total = one(db, f"SELECT count(*) AS n FROM members{where}", **params)  # noqa: S608
    count = int(total["n"]) if total else 0
    found = rows(
        db,
        f"SELECT {MEMBER_COLUMNS} FROM members{where}"  # noqa: S608 - fixed fragments, bound values
        f" ORDER BY {ORDER_BY[sort]} LIMIT :limit OFFSET :offset",
        **params,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return MemberPage(
        items=[Member.model_validate(row) for row in found],
        page=page,
        page_size=page_size,
        total=count,
        total_pages=math.ceil(count / page_size),
    )


@router.get(
    "/export.csv",
    response_class=Response,
    responses={
        200: {"content": {"text/csv": {}}, "description": "CSV attachment (members.csv)"},
        **problem_docs(HTTPStatus.UNAUTHORIZED),
    },
    summary=f"Export matching members as CSV (max {EXPORT_LIMIT}; no SSN)",
)
def export_members(db: Db, _: CurrentPrincipal, filters: Filters) -> Response:
    where, params = filters.where()
    found = rows(
        db,
        f"SELECT {', '.join(EXPORT_COLUMNS)} FROM members{where}"  # noqa: S608 - fixed fragments
        f" ORDER BY {ORDER_BY[MemberSort.MEMBER_ID]} LIMIT {EXPORT_LIMIT}",
        **params,
    )
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(EXPORT_COLUMNS)
    writer.writerows([row[column] for column in EXPORT_COLUMNS] for row in found)
    return Response(
        buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="members.csv"'},
    )


@router.get("/{member_id}", response_model=Member, responses=problem_docs(HTTPStatus.NOT_FOUND))
def get_member(db: Db, _: CurrentPrincipal, member_id: Annotated[MemberId, Path()]) -> Member:
    return Member.model_validate(_load(db, member_id))


def _load(db: Db, member_id: str) -> Row:
    row = one(db, f"SELECT {MEMBER_COLUMNS} FROM members WHERE member_id = :id", id=member_id)  # noqa: S608
    if row is None:
        raise _not_found(member_id)
    return row


@router.put(
    "/{member_id}",
    response_model=Member,
    responses=problem_docs(HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND, HTTPStatus.CONFLICT, UNPROCESSABLE),
    summary="Update a member (roles ADMIN, EXAMINER); send the current version",
)
def update_member(db: Db, _: Editor, member_id: Annotated[MemberId, Path()], update: MemberUpdate) -> Member:
    current = _load(db, member_id)
    if update.plan_code != current["plan_code"]:
        plan = one(db, "SELECT active FROM plans WHERE plan_code = :code", code=update.plan_code)
        if plan is None or not plan["active"]:
            raise ProblemError(
                UNPROCESSABLE,
                f"Plan {update.plan_code} does not exist or is closed to enrollment.",
                slug="plan-unavailable",
            )
    updated = one(
        db,
        f"UPDATE members SET email = :email, phone = :phone, address_line = :address_line, city = :city,"  # noqa: S608
        " state = :state, postal_code = :postal_code, status = :status, plan_code = :plan_code,"
        " version = version + 1, updated_at = now()"
        f" WHERE member_id = :id AND version = :version RETURNING {MEMBER_COLUMNS}",
        id=member_id,
        **update.model_dump(mode="json"),
    )
    if updated is None:
        raise ProblemError(
            HTTPStatus.CONFLICT,
            f"Member {member_id} was changed by someone else (current version {current['version']},"
            f" sent {update.version}). Reload and retry.",
            slug="stale-version",
        )
    return Member.model_validate(updated)


@router.get("/{member_id}/claims", response_model=list[Claim], responses=problem_docs(HTTPStatus.NOT_FOUND))
def member_claims(db: Db, _: CurrentPrincipal, member_id: Annotated[MemberId, Path()]) -> list[Claim]:
    _load(db, member_id)
    found = rows(
        db,
        f"SELECT {CLAIM_COLUMNS} FROM claims WHERE member_id = :id ORDER BY claim_id",  # noqa: S608
        id=member_id,
    )
    return [Claim.model_validate(row) for row in found]
