"""The import-linter contracts (ARCHITECTURE §3) must actually catch violations.

Each case copies the real package and pyproject.toml into a temp dir, injects one
import, and runs only the contract under test against the copy (PYTHONPATH puts
the copy first). Asserting "1 broken" for that contract means a config error can
never masquerade as a detected violation.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LINT_IMPORTS = "from importlinter.cli import lint_imports_command; lint_imports_command()"


def _run_contracts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    injected: dict[str, str],
    contract: str | None = None,
) -> subprocess.CompletedProcess[str]:
    shutil.copytree(REPO_ROOT / "src", tmp_path / "src")
    shutil.copy(REPO_ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    for module, import_line in injected.items():
        init = tmp_path / "src" / "paccaassure_taf" / module / "__init__.py"
        init.write_text(init.read_text(encoding="utf-8") + f"\n{import_line}\n", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "src"))
    monkeypatch.setenv("COLUMNS", "200")  # keep report lines unwrapped
    args = ["--no-cache", "--config", str(tmp_path / "pyproject.toml")]
    if contract:
        args += ["--contract", contract]
    return subprocess.run(
        [sys.executable, "-c", LINT_IMPORTS, *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def test_unmodified_package_satisfies_all_contracts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_contracts(tmp_path, monkeypatch, {})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "7 kept, 0 broken" in result.stdout


@pytest.mark.parametrize(
    ("contract", "module", "import_line"),
    [
        pytest.param("runtime-stack", "core", "import paccaassure_taf.bdd", id="1-core-imports-bdd"),
        pytest.param("runtime-stack", "elements", "import paccaassure_taf.web", id="1-elements-imports-web"),
        pytest.param("runtime-stack", "web", "import paccaassure_taf.api", id="1-independent-siblings"),
        pytest.param(
            "post-run-stack", "results", "import paccaassure_taf.history", id="2-results-imports-history"
        ),
        pytest.param(
            "post-run-isolation", "history", "import paccaassure_taf.web", id="3-history-imports-web"
        ),
        pytest.param(
            "runtime-isolation", "elements", "import paccaassure_taf.history", id="5-elements-imports-history"
        ),
        pytest.param("playwright-only-in-web", "core", "import playwright", id="4a-core-imports-playwright"),
        pytest.param("appium-only-in-desktop", "web", "import appium", id="4b-web-imports-appium"),
        pytest.param("behave-only-in-bdd", "results", "import behave", id="4c-results-imports-behave"),
    ],
)
def test_violation_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contract: str, module: str, import_line: str
) -> None:
    result = _run_contracts(tmp_path, monkeypatch, {module: import_line}, contract=contract)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "0 kept, 1 broken" in result.stdout
