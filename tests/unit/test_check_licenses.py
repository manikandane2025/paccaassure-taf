"""Unit tests for scripts/check_licenses.py (ADR-0010 amendment 1)."""

import importlib.util
import sys
from email.message import Message
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_licenses.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_licenses", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_licenses"] = module
    spec.loader.exec_module(module)
    return module


check_licenses = _load()
ALLOWED = frozenset({"MIT", "BSD-3-Clause", "Apache-2.0", "MPL-2.0", "PSF-2.0"})


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("MIT", True),
        ("Apache-2.0 OR UPL-1.0", True),  # python-oracledb: any allowed option passes
        ("UPL-1.0 OR Apache-2.0", True),
        ("MIT AND Apache-2.0", True),
        ("MIT AND GPL-3.0-only", False),  # AND needs every side allowed
        ("LGPL-3.0-only", False),  # psycopg: never a core dependency
        ("GPL-2.0-or-later", False),
        ("AGPL-3.0-only", False),  # k6
        ("(MIT OR GPL-3.0-only) AND BSD-3-Clause", True),
        ("Apache-2.0 WITH LLVM-exception", True),
        ("MIT License", False),  # free text is not SPDX; license_of() normalizes it first
        ("UNKNOWN", False),
        ("", False),
        ("MIT OR", False),  # malformed
    ],
)
def test_evaluate(expression: str, expected: bool) -> None:
    assert check_licenses.evaluate(expression, ALLOWED) is expected


class _FakeDist:
    def __init__(self, name: str, **headers: str | list[str]) -> None:
        self.metadata = Message()
        self.metadata["Name"] = name
        for key, value in headers.items():
            for item in value if isinstance(value, list) else [value]:
                self.metadata[key.replace("_", "-")] = item
        self.version = "1.0"


def test_license_expression_preferred_over_classifiers() -> None:
    dist = _FakeDist("a", License_Expression="MIT", Classifier="License :: OSI Approved :: BSD License")
    assert check_licenses.license_of(dist) == ("MIT", "License-Expression")


def test_multiple_classifiers_mean_choice() -> None:
    dist = _FakeDist(
        "b",
        Classifier=[
            "License :: OSI Approved :: MIT License",
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        ],
    )
    license_text, source = check_licenses.license_of(dist)
    assert source == "Classifier"
    assert check_licenses.evaluate(license_text, ALLOWED)


def test_missing_metadata_fails() -> None:
    policy = check_licenses.Policy(allowed=ALLOWED, skip=frozenset())
    verdicts = check_licenses.check([_FakeDist("mystery")], policy)
    assert verdicts[0].license == "UNKNOWN"
    assert not verdicts[0].allowed


def test_exception_requires_reason() -> None:
    policy = check_licenses.Policy(
        allowed=ALLOWED, skip=frozenset(), exceptions={"isc-pkg": {"license": "ISC", "approved": True}}
    )
    assert not check_licenses.check([_FakeDist("isc-pkg")], policy)[0].allowed


def test_real_policy_file_is_valid() -> None:
    policy = check_licenses.Policy.load(check_licenses.DEFAULT_POLICY)
    assert "MIT" in policy.allowed
    assert "LGPL-3.0-only" not in policy.allowed
    assert all(str(e.get("reason", "")).strip() for e in policy.exceptions.values())


def test_free_text_is_normalized_before_evaluation() -> None:
    assert check_licenses.normalize("MIT License") == "MIT"
    dist = _FakeDist("c", License="MIT License")
    assert check_licenses.license_of(dist) == ("MIT", "License")
