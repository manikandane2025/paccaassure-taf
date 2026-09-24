"""License verification tests. Signing happens here only: the signer never ships in the wheel."""

import base64
import json
from datetime import date
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from paccaassure_taf.core.errors import LicenseError
from paccaassure_taf.core.license import (
    TRUSTED_PUBLIC_KEYS,
    Entitlement,
    LicenseState,
    canonical_bytes,
    check_license,
    load_license,
)

TODAY = date(2026, 9, 24)


def _public_bytes(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


@pytest.fixture
def signer() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def _payload(expires: date, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "format_version": 1,
        "license_id": "NWH-2026-001",
        "licensee": "Northwind Health",
        "issued": "2026-01-01",
        "expires": expires.isoformat(),
        "seats": 25,
        "entitlements": ["desktop", "sinks.powerbi"],
    }
    payload.update(extra)
    return payload


def _write(path: Path, payload: dict[str, object], key: Ed25519PrivateKey) -> Path:
    signature = base64.b64encode(key.sign(canonical_bytes(payload))).decode()
    path.write_text(json.dumps({"payload": payload, "signature": signature}, indent=2), encoding="utf-8")
    return path


def test_valid_license_entitles_listed_extras(tmp_path: Path, signer: Ed25519PrivateKey) -> None:
    path = _write(tmp_path / "license.json", _payload(date(2027, 6, 30)), signer)
    status = check_license(path, today=TODAY, public_keys=[_public_bytes(signer)])
    assert status.state is LicenseState.VALID
    assert status.banner is None
    assert status.entitles(Entitlement.DESKTOP)
    assert status.entitles(Entitlement.SINKS_POWERBI)
    assert not status.entitles(Entitlement.JSP)
    assert status.payload is not None
    assert status.payload.seats == 25


def test_expiring_soon_still_entitles_but_warns(tmp_path: Path, signer: Ed25519PrivateKey) -> None:
    path = _write(tmp_path / "license.json", _payload(date(2026, 10, 10)), signer)
    status = check_license(path, today=TODAY, public_keys=[_public_bytes(signer)])
    assert status.state is LicenseState.EXPIRING_SOON
    assert status.days_left == 16
    assert status.entitles(Entitlement.DESKTOP)
    assert status.banner == "License NWH-2026-001 expires on 2026-10-10 (16 days)."


def test_expired_license_degrades_gracefully(tmp_path: Path, signer: Ed25519PrivateKey) -> None:
    path = _write(tmp_path / "license.json", _payload(date(2026, 9, 1)), signer)
    status = check_license(path, today=TODAY, public_keys=[_public_bytes(signer)])
    assert status.state is LicenseState.EXPIRED
    assert status.days_left == -23
    assert not status.entitles(Entitlement.DESKTOP)
    assert status.banner is not None
    assert "core tests still run" in status.banner


def test_expires_today_is_still_usable(tmp_path: Path, signer: Ed25519PrivateKey) -> None:
    path = _write(tmp_path / "license.json", _payload(TODAY), signer)
    assert (
        check_license(path, today=TODAY, public_keys=[_public_bytes(signer)]).state
        is LicenseState.EXPIRING_SOON
    )


def test_tampered_payload_is_invalid(tmp_path: Path, signer: Ed25519PrivateKey) -> None:
    path = _write(tmp_path / "license.json", _payload(date(2027, 1, 1)), signer)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["payload"]["expires"] = "2099-12-31"
    path.write_text(json.dumps(document), encoding="utf-8")
    status = check_license(path, today=TODAY, public_keys=[_public_bytes(signer)])
    assert status.state is LicenseState.INVALID
    assert not status.entitles(Entitlement.DESKTOP)


def test_signature_from_untrusted_key_is_invalid(tmp_path: Path, signer: Ed25519PrivateKey) -> None:
    path = _write(tmp_path / "license.json", _payload(date(2027, 1, 1)), signer)
    other = Ed25519PrivateKey.generate()
    assert check_license(path, today=TODAY, public_keys=[_public_bytes(other)]).state is LicenseState.INVALID


def test_any_trusted_key_may_sign_and_bad_keys_are_skipped(tmp_path: Path, signer: Ed25519PrivateKey) -> None:
    path = _write(tmp_path / "license.json", _payload(date(2027, 1, 1)), signer)
    keys = [b"not-a-key", _public_bytes(Ed25519PrivateKey.generate()), _public_bytes(signer)]
    assert check_license(path, today=TODAY, public_keys=keys).state is LicenseState.VALID


def test_no_trusted_keys_until_release(tmp_path: Path, signer: Ed25519PrivateKey) -> None:
    assert TRUSTED_PUBLIC_KEYS == ()
    path = _write(tmp_path / "license.json", _payload(date(2027, 1, 1)), signer)
    assert check_license(path, today=TODAY).state is LicenseState.INVALID


def test_missing_license(tmp_path: Path) -> None:
    assert check_license(None, today=TODAY).state is LicenseState.MISSING
    status = check_license(tmp_path / "nope.json", today=TODAY)
    assert status.state is LicenseState.MISSING
    assert "not found" in status.message


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '["a list"]',
        '{"payload": {}, "signature": "c2ln"}',
        '{"payload": {"license_id": "x"}, "signature": 5}',
        '{"payload": ' + json.dumps(_payload(date(2027, 1, 1))) + ', "signature": "***not base64***"}',
        '{"payload": ' + json.dumps(_payload(date(2027, 1, 1), extra_field=1)) + ', "signature": "c2ln"}',
    ],
)
def test_malformed_files_are_invalid_not_crashes(tmp_path: Path, content: str) -> None:
    path = tmp_path / "license.json"
    path.write_text(content, encoding="utf-8")
    status = check_license(path, today=TODAY, public_keys=[b"x" * 32])
    assert status.state is LicenseState.INVALID
    with pytest.raises(LicenseError):
        load_license(path)


def test_unreadable_file_raises_on_load(tmp_path: Path) -> None:
    with pytest.raises(LicenseError, match="could not be read"):
        load_license(tmp_path)  # a directory


def test_canonical_bytes_are_order_independent() -> None:
    assert canonical_bytes({"b": 1, "a": 2}) == canonical_bytes({"a": 2, "b": 1})
