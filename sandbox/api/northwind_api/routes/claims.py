"""Claims: list with paging, detail, submit (201 created, 409 duplicate external_ref, 422 invalid)."""

import datetime as dt
import math
from http import HTTPStatus
from typing import Annotated

import pg8000.exceptions
from fastapi import APIRouter, Path, Query, Response

from northwind_api.db import UNIQUE_VIOLATION, Db, one, rows, sql_state
from northwind_api.models import (
    Claim,
    ClaimCreate,
    ClaimPage,
    ClaimStatus,
    FieldError,
    MemberId,
    MemberStatus,
)
from northwind_api.problems import UNPROCESSABLE, ProblemError, problem_docs
from northwind_api.security import CurrentPrincipal, Editor

router = APIRouter(prefix="/claims", tags=["claims"])

CLAIM_COLUMNS = (
    "claim_id, member_id, external_ref, service_date, submitted_at, provider_name, diagnosis_code,"
    " amount, status, notes"
)


@router.get("", response_model=ClaimPage, responses=problem_docs(HTTPStatus.UNAUTHORIZED, UNPROCESSABLE))
def list_claims(
    db: Db,
    _: CurrentPrincipal,
    member_id: Annotated[MemberId | None, Query()] = None,
    status: Annotated[ClaimStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ClaimPage:
    where = (
        " WHERE (CAST(:member_id AS text) IS NULL OR member_id = :member_id)"
        " AND (CAST(:status AS text) IS NULL OR status = :status)"
    )
    params: dict[str, object] = {"member_id": member_id, "status": status.value if status else None}
    total = one(db, f"SELECT count(*) AS n FROM claims{where}", **params)  # noqa: S608
    count = int(total["n"]) if total else 0
    found = rows(
        db,
        f"SELECT {CLAIM_COLUMNS} FROM claims{where} ORDER BY claim_id LIMIT :limit OFFSET :offset",  # noqa: S608
        **params,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return ClaimPage(
        items=[Claim.model_validate(row) for row in found],
        page=page,
        page_size=page_size,
        total=count,
        total_pages=math.ceil(count / page_size),
    )


@router.get("/{claim_id}", response_model=Claim, responses=problem_docs(HTTPStatus.NOT_FOUND))
def get_claim(db: Db, _: CurrentPrincipal, claim_id: Annotated[str, Path(pattern=r"^NWH-C\d{7}$")]) -> Claim:
    row = one(db, f"SELECT {CLAIM_COLUMNS} FROM claims WHERE claim_id = :id", id=claim_id)  # noqa: S608
    if row is None:
        raise ProblemError(HTTPStatus.NOT_FOUND, f"Claim {claim_id} does not exist.", slug="not-found")
    return Claim.model_validate(row)


def _invalid(field: str, message: str) -> ProblemError:
    return ProblemError(
        UNPROCESSABLE,
        "The claim breaks a business rule; see errors.",
        slug="claim-rejected",
        errors=[FieldError(field=f"body.{field}", message=message, type="business_rule")],
    )


def _duplicate(db: Db, external_ref: str) -> ProblemError | None:
    existing = one(db, "SELECT claim_id FROM claims WHERE external_ref = :ref", ref=external_ref)
    if existing is None:
        return None
    return ProblemError(
        HTTPStatus.CONFLICT,
        f"A claim with external_ref {external_ref} already exists.",
        slug="duplicate-claim",
        existing_claim_id=existing["claim_id"],
    )


@router.post(
    "",
    response_model=Claim,
    status_code=HTTPStatus.CREATED,
    responses=problem_docs(HTTPStatus.FORBIDDEN, HTTPStatus.CONFLICT, UNPROCESSABLE),
    summary="Submit a claim (roles ADMIN, EXAMINER)",
)
def submit_claim(db: Db, _: Editor, claim: ClaimCreate, response: Response) -> Claim:
    member = one(db, "SELECT status FROM members WHERE member_id = :id", id=claim.member_id)
    if member is None:
        raise _invalid("member_id", f"Member {claim.member_id} does not exist.")
    if member["status"] != MemberStatus.ACTIVE:
        raise _invalid("member_id", f"Member {claim.member_id} is {member['status']}; claims need ACTIVE.")
    if claim.service_date > dt.datetime.now(dt.UTC).date():
        raise _invalid("service_date", "The service date is in the future.")
    if (conflict := _duplicate(db, claim.external_ref)) is not None:
        raise conflict
    try:
        created = one(
            db,
            "INSERT INTO claims (member_id, external_ref, service_date, submitted_at, provider_name,"  # noqa: S608
            " diagnosis_code, amount, status, notes) VALUES (:member_id, :external_ref, :service_date,"
            " now(), :provider_name, :diagnosis_code, :amount, 'SUBMITTED', :notes)"
            f" RETURNING {CLAIM_COLUMNS}",
            **claim.model_dump(),
        )
    except pg8000.exceptions.DatabaseError as error:
        # Lost a race with an identical submission: same answer as the pre-check.
        if sql_state(error) == UNIQUE_VIOLATION and (conflict := _duplicate(db, claim.external_ref)):
            raise conflict from error
        raise
    if created is None:
        raise RuntimeError("INSERT ... RETURNING returned no row")
    response.headers["Location"] = f"/claims/{created['claim_id']}"
    return Claim.model_validate(created)
