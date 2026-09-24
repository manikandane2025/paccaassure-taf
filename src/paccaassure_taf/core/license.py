"""Offline license verification (ADR-0010) — checked only at CLI entry points.

A license file is JSON: ``{"payload": {...}, "signature": "<base64 Ed25519 signature>"}``.
The signature covers the payload's canonical JSON bytes (sorted keys, no whitespace).
Verification never phones home and **never breaks a run**: an expired, missing or invalid
license degrades to core features with a report banner (PRODUCT §3).

The signing tool is deliberately *not* part of this package. The production public key is
embedded at release time (BUILD_PLAN Phase 11); until then ``TRUSTED_PUBLIC_KEYS`` is empty
and callers pass keys explicitly (tests use their own throwaway key pairs).

Example:
    >>> from datetime import date
    >>> status = check_license(None, today=date(2026, 9, 24))
    >>> status.state, status.entitles(Entitlement.DESKTOP), status.banner is not None
    (<LicenseState.MISSING: 'missing'>, False, True)
"""

import base64
import binascii
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, ValidationError

from paccaassure_taf.core.errors import LicenseError

__all__ = [
    "TRUSTED_PUBLIC_KEYS",
    "Entitlement",
    "LicensePayload",
    "LicenseState",
    "LicenseStatus",
    "SignedLicense",
    "canonical_bytes",
    "check_license",
    "load_license",
]

# Raw 32-byte Ed25519 public keys trusted to sign licenses. Production key added at release (Phase 11).
TRUSTED_PUBLIC_KEYS: Final[tuple[bytes, ...]] = ()
DEFAULT_WARN_DAYS: Final = 30


class Entitlement(StrEnum):
    """Licensed extras. Core features (web, API, BDD, report, SQLite history) need no entitlement.

    Example:
        >>> Entitlement("sinks.powerbi") is Entitlement.SINKS_POWERBI
        True
    """

    DESKTOP = "desktop"
    JSP = "jsp"
    HISTORY_SHARED = "history.shared"
    PARALLEL = "parallel"
    SINKS_ADO = "sinks.ado"
    SINKS_JIRA = "sinks.jira"
    SINKS_POWERBI = "sinks.powerbi"


class LicensePayload(BaseModel):
    """What a license grants. Signed as canonical JSON.

    Example:
        >>> LicensePayload(license_id="L-1", licensee="Northwind Health", issued=date(2026, 1, 1),
        ...                expires=date(2027, 1, 1), entitlements={Entitlement.DESKTOP}).seats is None
        True
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: Literal[1] = 1
    license_id: str = Field(min_length=1)
    licensee: str = Field(min_length=1)
    issued: date
    expires: date
    seats: PositiveInt | None = None
    entitlements: frozenset[Entitlement] = frozenset()


@dataclass(frozen=True)
class SignedLicense:
    """A parsed license file: the payload as signed (raw) and validated, plus its signature.

    Example:
        >>> SignedLicense  # produced by load_license()
        <class 'paccaassure_taf.core.license.SignedLicense'>
    """

    raw_payload: dict[str, object]
    payload: LicensePayload
    signature: bytes


class LicenseState(StrEnum):
    """Outcome of a license check.

    Example:
        >>> LicenseState.EXPIRING_SOON.value
        'expiring_soon'
    """

    VALID = "valid"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    MISSING = "missing"
    INVALID = "invalid"


@dataclass(frozen=True)
class LicenseStatus:
    """Result of :func:`check_license`; drives entitlements and the report banner.

    Example:
        >>> LicenseStatus(LicenseState.MISSING, None, "No license file configured.").entitles(Entitlement.JSP)
        False
    """

    state: LicenseState
    payload: LicensePayload | None
    message: str
    days_left: int | None = None

    def entitles(self, entitlement: Entitlement) -> bool:
        """True if the licensed extra may be used now (valid or expiring-soon licenses only).

        Example:
            >>> LicenseStatus(LicenseState.EXPIRED, None, "Expired.").entitles(Entitlement.DESKTOP)
            False
        """
        usable = self.state in {LicenseState.VALID, LicenseState.EXPIRING_SOON}
        return usable and self.payload is not None and entitlement in self.payload.entitlements

    @property
    def banner(self) -> str | None:
        """Text for the report/CLI banner, or None when the license is simply valid.

        Example:
            >>> LicenseStatus(LicenseState.VALID, None, "ok").banner is None
            True
        """
        return None if self.state is LicenseState.VALID else self.message


def canonical_bytes(raw_payload: dict[str, object]) -> bytes:
    """Return the exact bytes a license signature covers.

    Example:
        >>> canonical_bytes({"b": 1, "a": "x"})
        b'{"a":"x","b":1}'
    """
    return json.dumps(raw_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def load_license(path: Path) -> SignedLicense:
    """Read and structurally validate a license file (no signature or expiry check).

    Raises:
        LicenseError: If the file is unreadable, not JSON, or not a valid license document.

    Example:
        >>> load_license(Path("no-such-license.json"))  # doctest: +SKIP
        Traceback (most recent call last):
        paccaassure_taf.core.errors.LicenseError: License file no-such-license.json could not be read
    """
    try:
        document: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise LicenseError(
            f"License file {path} could not be read",
            cause=f"{type(error).__name__}: {error.strerror}",
            fix="Check license.file in config and the file permissions.",
        ) from error
    except json.JSONDecodeError as error:
        raise LicenseError(
            f"License file {path} is not valid JSON", cause=str(error), fix=_REISSUE
        ) from error
    if not (
        isinstance(document, dict)
        and isinstance(document.get("payload"), dict)
        and isinstance(document.get("signature"), str)
    ):
        raise LicenseError(
            f"License file {path} is not a license", cause="expected 'payload' and 'signature'", fix=_REISSUE
        )
    raw_payload: dict[str, object] = document["payload"]
    try:
        payload = LicensePayload.model_validate(raw_payload)
        signature = base64.b64decode(document["signature"], validate=True)
    except (ValidationError, binascii.Error) as error:
        raise LicenseError(f"License file {path} is malformed", cause=str(error).splitlines()[0],
                           fix=_REISSUE) from error  # fmt: skip
    return SignedLicense(raw_payload=raw_payload, payload=payload, signature=signature)


_REISSUE: Final = "Use the license file exactly as issued; request a re-issue if it was edited or truncated."


def check_license(
    path: Path | None,
    *,
    today: date,
    public_keys: Sequence[bytes] = TRUSTED_PUBLIC_KEYS,
    warn_days: int = DEFAULT_WARN_DAYS,
) -> LicenseStatus:
    """Verify a license file offline. Never raises: problems become a degraded status.

    Args:
        path: License file (``license.file`` in config), or None if not configured.
        today: The current date (explicit, so checks are deterministic).
        public_keys: Trusted raw Ed25519 public keys.
        warn_days: Days before expiry from which the state is ``EXPIRING_SOON``.

    Example:
        >>> check_license(Path("missing.json"), today=date(2026, 9, 24)).state
        <LicenseState.MISSING: 'missing'>
    """
    if path is None or not path.exists():
        where = (
            "No license file configured (license.file)" if path is None else f"License file {path} not found"
        )
        return LicenseStatus(LicenseState.MISSING, None, f"{where}; running with core features only.")
    try:
        signed = load_license(path)
    except LicenseError as error:
        return LicenseStatus(LicenseState.INVALID, None, f"{error.what}; running with core features only.")
    if not _signature_valid(signed, public_keys):
        return LicenseStatus(
            LicenseState.INVALID,
            None,
            "License signature does not match a trusted PaccaAssureTAF key; running with core features only.",
        )
    payload = signed.payload
    days_left = (payload.expires - today).days
    if days_left < 0:
        return LicenseStatus(
            LicenseState.EXPIRED,
            payload,
            f"License {payload.license_id} for {payload.licensee} expired on {payload.expires.isoformat()}; "
            "licensed extras are disabled, core tests still run. "
            "Contact your PaccaAssureTAF vendor to renew.",
            days_left,
        )
    if days_left <= warn_days:
        return LicenseStatus(
            LicenseState.EXPIRING_SOON,
            payload,
            f"License {payload.license_id} expires on {payload.expires.isoformat()} ({days_left} days).",
            days_left,
        )
    return LicenseStatus(LicenseState.VALID, payload, f"License {payload.license_id} is valid.", days_left)


def _signature_valid(signed: SignedLicense, public_keys: Sequence[bytes]) -> bool:
    message = canonical_bytes(signed.raw_payload)
    for raw_key in public_keys:
        try:
            Ed25519PublicKey.from_public_bytes(raw_key).verify(signed.signature, message)
        except (InvalidSignature, ValueError):
            continue
        return True
    return False
