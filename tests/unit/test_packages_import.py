"""Smoke test for the package skeleton (BUILD_PLAN Phase 0).

Every subpackage of paccaassure_taf must import cleanly (no import-time side
effects), document itself, declare its public API, and carry a nested CLAUDE.md
within the AI_NATIVE size budget.
"""

import importlib
import pkgutil
from pathlib import Path

import pytest

import paccaassure_taf

PACKAGE_ROOT = Path(paccaassure_taf.__file__).parent
REPO_ROOT = PACKAGE_ROOT.parents[1]

# ARCHITECTURE §2: the packages the architecture promises. Adding a package means updating the docs too.
EXPECTED_PACKAGES = {
    "core", "elements", "web", "jsp", "api", "desktop", "data", "flows", "bdd",
    "results", "evidence", "reporting", "history", "gates", "sinks", "runner",
}  # fmt: skip
NESTED_CLAUDE_MAX_LINES = 60
ROOT_CLAUDE_MAX_LINES = 150


def _subpackages() -> list[str]:
    return sorted(m.name for m in pkgutil.iter_modules([str(PACKAGE_ROOT)]) if m.ispkg)


def test_package_set_matches_architecture() -> None:
    assert set(_subpackages()) == EXPECTED_PACKAGES


@pytest.mark.parametrize("name", _subpackages())
def test_subpackage_imports_and_documents_itself(name: str) -> None:
    module = importlib.import_module(f"paccaassure_taf.{name}")
    assert module.__doc__, f"paccaassure_taf.{name} needs a module docstring"
    assert "Example:" in module.__doc__, f"paccaassure_taf.{name} docstring needs an Example (hard rule 9)"
    exported = getattr(module, "__all__", None)
    assert isinstance(exported, list), f"paccaassure_taf.{name} must declare __all__"
    for symbol in exported:
        assert hasattr(module, symbol), f"__all__ lists missing name {symbol!r}"


@pytest.mark.parametrize("name", _subpackages())
def test_subpackage_has_nested_claude_md(name: str) -> None:
    claude = PACKAGE_ROOT / name / "CLAUDE.md"
    assert claude.is_file(), f"{claude} is required (ARCHITECTURE §2)"
    lines = claude.read_text(encoding="utf-8").splitlines()
    assert lines[0] == f"# paccaassure_taf.{name}"
    assert len(lines) < NESTED_CLAUDE_MAX_LINES


def test_root_claude_md_within_budget() -> None:
    lines = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
    assert len(lines) < ROOT_CLAUDE_MAX_LINES


def test_package_is_typed() -> None:
    assert (PACKAGE_ROOT / "py.typed").is_file()
