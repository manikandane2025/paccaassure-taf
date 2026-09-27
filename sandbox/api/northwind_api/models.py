"""Request and response models (they drive the OpenAPI document)."""

import datetime as dt
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

# Money: validated as an exact 2-decimal Decimal, emitted as a JSON number.
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
MemberId = Annotated[str, Field(pattern=r"^NWH-M\d{6}$", examples=["NWH-M000123"])]
PlanCode = Annotated[str, Field(pattern=r"^NWH-P\d{3}$", examples=["NWH-P003"])]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Role(StrEnum):
    ADMIN = "ADMIN"
    EXAMINER = "EXAMINER"
    VIEWER = "VIEWER"


class MemberStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING = "PENDING"


class ClaimStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    PAID = "PAID"


class PlanTier(StrEnum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"


class MemberSort(StrEnum):
    LAST_NAME = "last_name"
    MEMBER_ID = "member_id"
    DATE_OF_BIRTH = "date_of_birth"


# ---------------------------------------------------------------- auth
class PasswordGrant(_Strict):
    grant_type: Literal["password"] = "password"
    username: str = Field(min_length=1, max_length=40, examples=["examiner"])
    password: str = Field(min_length=1, max_length=200, examples=["pw-Northwind-examiner"])


class ClientCredentialsGrant(_Strict):
    grant_type: Literal["client_credentials"]
    client_id: str = Field(min_length=1, max_length=40, examples=["nwh-batch"])
    client_secret: str = Field(min_length=1, max_length=200, examples=["cs-Northwind-batch"])


TokenRequest = Annotated[PasswordGrant | ClientCredentialsGrant, Field(discriminator="grant_type")]


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - OAuth2 token type, not a secret
    expires_in: int = Field(description="Seconds until the token expires.")
    role: Role
    display_name: str


class Principal(BaseModel):
    subject: str
    display_name: str
    role: Role
    kind: Literal["user", "client"]
    expires_at: dt.datetime


# ---------------------------------------------------------------- plans
class Plan(BaseModel):
    plan_code: PlanCode
    name: str
    tier: PlanTier
    monthly_premium: Money
    deductible: Money
    active: bool
    description: str


# ---------------------------------------------------------------- members
class Member(BaseModel):
    member_id: MemberId
    first_name: str
    last_name: str
    date_of_birth: dt.date
    ssn: str = Field(description="Synthetic SSN-shaped value (always 9xx). Sensitive: mask in evidence.")
    email: str
    phone: str
    address_line: str
    city: str
    state: str
    postal_code: str
    status: MemberStatus
    plan_code: PlanCode
    enrolled_on: dt.date
    version: int = Field(description="Send back on update; a stale version is a 409.")
    updated_at: dt.datetime


class MemberUpdate(_Strict):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=120)
    phone: str = Field(pattern=r"^\d{3}-\d{3}-\d{4}$", examples=["404-555-0123"])
    address_line: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=40)
    state: str = Field(pattern=r"^[A-Z]{2}$")
    postal_code: str = Field(pattern=r"^\d{5}$")
    status: MemberStatus
    plan_code: PlanCode
    version: int = Field(ge=1)


class MemberPage(BaseModel):
    items: list[Member]
    page: int
    page_size: int
    total: int
    total_pages: int


# ---------------------------------------------------------------- claims
class Claim(BaseModel):
    claim_id: str = Field(examples=["NWH-C0000001"])
    member_id: MemberId
    external_ref: str
    service_date: dt.date
    submitted_at: dt.datetime
    provider_name: str
    diagnosis_code: str
    amount: Money
    status: ClaimStatus
    notes: str


class ClaimCreate(_Strict):
    member_id: MemberId
    external_ref: str = Field(
        min_length=1, max_length=40, description="Submitter's id; resubmitting it is a 409."
    )
    service_date: dt.date
    provider_name: str = Field(min_length=1, max_length=80)
    diagnosis_code: str = Field(pattern=r"^[A-Z]\d{2}(\.[0-9A-Z]{1,4})?$", examples=["J06.9"])
    amount: Money = Field(gt=0, le=Decimal("1000000"), max_digits=10, decimal_places=2)
    notes: str = Field(default="", max_length=500)


class ClaimPage(BaseModel):
    items: list[Claim]
    page: int
    page_size: int
    total: int
    total_pages: int


# ---------------------------------------------------------------- misc
class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    version: str


class ResetResult(BaseModel):
    status: Literal["reset"] = "reset"
    plans: int
    members: int
    claims: int


class FieldError(BaseModel):
    field: str = Field(description="Dotted location, e.g. body.amount or query.page.")
    message: str
    type: str


class Problem(BaseModel):
    """RFC 9457 problem details (media type application/problem+json)."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    errors: list[FieldError] | None = None
    existing_claim_id: str | None = Field(default=None, description="Set on a duplicate-claim 409.")
