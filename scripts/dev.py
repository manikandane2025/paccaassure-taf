"""Cross-shell developer and CI task runner for paccaassure-taf-core (ADR-0014).

Every quality check lives here so that developers, pre-commit and every CI
system (GitHub Actions today; Azure Pipelines / Jenkins later) run exactly the
same commands. Works unchanged in PowerShell 5.1/7, cmd, bash and zsh.

Example:
    uv run python scripts/dev.py check
    uv run python scripts/dev.py lint typecheck
    uv run python scripts/dev.py --help
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import sysconfig
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DIR = REPO_ROOT / "sandbox"


def tool(name: str) -> str:
    """Return the path of a console script installed in the active environment.

    Resolving through the environment's scripts directory (not PATH) guarantees
    the locked tool version is used, on every OS.

    Example:
        tool("ruff")  # -> ".../.venv/Scripts/ruff.exe" on Windows
    """
    scripts_dir = Path(sysconfig.get_path("scripts"))
    for candidate in (scripts_dir / name, scripts_dir / f"{name}.exe"):
        if candidate.exists():
            return str(candidate)
    return name


def python_module(module: str, *args: str) -> list[str]:
    """Build a command that runs ``python -m <module>`` with the current interpreter.

    Example:
        python_module("pytest", "tests/unit")
    """
    return [sys.executable, "-m", module, *args]


@dataclass(frozen=True)
class Task:
    """A named dev task: one or more commands run from the repository root."""

    name: str
    help: str
    commands: Callable[[], list[list[str]]]


def _lint() -> list[list[str]]:
    return [[tool("ruff"), "check", "."]]


def _format_check() -> list[list[str]]:
    return [[tool("ruff"), "format", "--check", "."]]


def _format() -> list[list[str]]:
    # Format first: it resolves line-length issues that `check --fix` cannot.
    return [[tool("ruff"), "format", "."], [tool("ruff"), "check", "--fix", "."]]


def _typecheck() -> list[list[str]]:
    return [python_module("mypy")]


def lint_imports(*args: str) -> list[str]:
    """Build an import-linter command that runs through the interpreter.

    Console-script ``.exe`` launchers can be blocked by endpoint security on
    managed Windows machines; ``python -c`` is not. Use this everywhere.

    Example:
        lint_imports("--no-cache", "--contract", "runtime-stack")
    """
    code = "from importlinter.cli import lint_imports_command; lint_imports_command()"
    return [sys.executable, "-c", code, *args]


def _imports() -> list[list[str]]:
    return [lint_imports("--no-cache")]


def _test() -> list[list[str]]:
    # Unit tests + every docstring example in src (hard rule 9: examples must run).
    return [python_module("pytest", "tests/unit", "src/paccaassure_taf", "--doctest-modules")]


def _coverage() -> list[list[str]]:
    # Phase 1 acceptance: >= 90% line+branch coverage on paccaassure_taf.core.
    return [
        python_module(
            "pytest", "tests/unit", "--cov=paccaassure_taf.core", "--cov-report=term-missing",
            "--cov-fail-under=90",
        )
    ]  # fmt: skip


def _licenses() -> list[list[str]]:
    # Run after `uv sync --all-extras` so every extra and dev tool is inspected.
    return [[sys.executable, str(REPO_ROOT / "scripts" / "check_licenses.py")]]


def _uv() -> str:
    return os.environ.get("UV", "uv")  # `uv run` exports UV=<path to uv>


def _audit() -> list[list[str]]:
    # Audit the locked, fully pinned dependency set (all extras) without needing pip in the venv.
    requirements = REPO_ROOT / ".pataf-audit-requirements.txt"
    uv = _uv()
    return [
        [uv, "export", "--frozen", "--all-extras", "--no-emit-project", "--quiet",
         "--output-file", str(requirements)],
        python_module("pip_audit", "--requirement", str(requirements), "--disable-pip",
                      "--progress-spinner", "off"),
    ]  # fmt: skip


GITLEAKS_IMAGE = "ghcr.io/gitleaks/gitleaks:v8.30.1"


def _gitleaks(*args: str) -> list[str]:
    # The repo is bind-mounted read-only; safe.directory avoids git's "dubious ownership" refusal.
    return [
        "docker", "run", "--rm", "-v", f"{REPO_ROOT}:/repo:ro",
        "-e", "GIT_CONFIG_COUNT=1", "-e", "GIT_CONFIG_KEY_0=safe.directory", "-e", "GIT_CONFIG_VALUE_0=*",
        GITLEAKS_IMAGE, *args, "--redact", "--no-banner",
    ]  # fmt: skip


def _docker_available() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0
    except OSError:
        return False


def _hooks() -> list[list[str]]:
    return [python_module("pre_commit", "run", "--all-files", "--show-diff-on-failure")]


def _secrets() -> list[list[str]]:
    # Full git history, fail-closed (CI). Fails if Docker is unavailable.
    return [_gitleaks("git", "/repo")]


def _secrets_staged() -> list[list[str]]:
    # Staged changes only (pre-commit). Fails open with a warning when Docker is down locally;
    # CI's full-history `secrets` task is the enforcing gate.
    if not _docker_available():
        print("WARNING: Docker is not running; gitleaks skipped locally. CI will scan full history.")
        return []
    return [_gitleaks("git", "/repo", "--pre-commit", "--staged")]


def sandbox_compose(*args: str) -> list[str]:
    """Build a ``docker compose`` command for the Northwind Health sandbox.

    Example:
        sandbox_compose("ps")  # -> ["docker", "compose", "-f", ".../sandbox/compose.yaml", "ps"]
    """
    return ["docker", "compose", "-f", str(SANDBOX_DIR / "compose.yaml"), *args]


def ensure_sandbox_env(sandbox_dir: Path = SANDBOX_DIR) -> bool:
    """Create ``sandbox/.env`` from ``sandbox/env.example`` if missing; never overwrite local edits.

    Returns True if the file was created.

    Example:
        ensure_sandbox_env()  # first run: copies env.example -> .env and returns True
    """
    env_file = sandbox_dir / ".env"
    if env_file.exists():
        return False
    shutil.copyfile(sandbox_dir / "env.example", env_file)
    print("Created sandbox/.env from sandbox/env.example; edit it to change ports (it is gitignored).")
    return True


def _sandbox_smoke() -> list[list[str]]:
    return [[sys.executable, str(REPO_ROOT / "scripts" / "sandbox_smoke.py")]]


def _sandbox_up() -> list[list[str]]:
    ensure_sandbox_env()
    return [sandbox_compose("up", "-d", "--build", "--wait", "--wait-timeout", "300"), *_sandbox_smoke()]


def _sandbox_down() -> list[list[str]]:
    # -v removes the data volume: the next sandbox-up reseeds from sandbox/postgres/initdb.
    return [sandbox_compose("down", "-v", "--remove-orphans")]


def _sandbox_api(*args: str) -> list[str]:
    # The sandbox API is its own uv project (sandbox/api/uv.lock, sandbox/api/.venv).
    return [_uv(), "run", "--project", str(SANDBOX_DIR / "api"), "--frozen", "python", *args]


def _sandbox_typecheck() -> list[list[str]]:
    # Standard mypy (not --strict) for sandbox Python. The web app's tsc runs in its image build.
    api = SANDBOX_DIR / "api"
    return [
        _sandbox_api("-m", "mypy", "--config-file", str(api / "pyproject.toml"), str(api / "northwind_api"))
    ]


def _sandbox_licenses() -> list[list[str]]:
    # ADR-0010: sandbox dependencies never ship but are checked too, separately from core.
    checker = str(REPO_ROOT / "scripts" / "check_licenses.py")
    return [
        _sandbox_api(checker),
        [sys.executable, checker, "--npm-lock", str(SANDBOX_DIR / "web" / "package-lock.json")],
    ]


TASKS: dict[str, Task] = {
    task.name: task
    for task in (
        Task("lint", "ruff lint (no fixes)", _lint),
        Task("format-check", "ruff format --check", _format_check),
        Task("format", "apply ruff fixes and formatting", _format),
        Task("typecheck", "mypy --strict (config in pyproject.toml)", _typecheck),
        Task("imports", "import-linter layer contracts (ARCHITECTURE §3)", _imports),
        Task("test", "unit tests + docstring examples (doctest)", _test),
        Task("coverage", "unit tests with >=90% coverage gate on core", _coverage),
        Task("licenses", "third-party license allow-list (ADR-0010)", _licenses),
        Task("audit", "known-vulnerability audit of locked deps (network)", _audit),
        Task("hooks", "all pre-commit hooks on all files", _hooks),
        Task("secrets", "gitleaks over full git history (Docker; CI)", _secrets),
        Task("secrets-staged", "gitleaks over staged changes (Docker; pre-commit)", _secrets_staged),
        Task("sandbox-up", "build + start the sandbox, wait until healthy, smoke-probe it", _sandbox_up),
        Task("sandbox-smoke", "container health + one probe per sandbox app", _sandbox_smoke),
        Task("sandbox-down", "stop the sandbox and delete its data volume", _sandbox_down),
        Task("sandbox-typecheck", "standard mypy on the sandbox API", _sandbox_typecheck),
        Task("sandbox-licenses", "license allow-list for sandbox Python + npm deps", _sandbox_licenses),
    )
}

# Aggregate run by CI and before every PR. Order: fastest feedback first.
CHECK_SEQUENCE: tuple[str, ...] = ("lint", "format-check", "typecheck", "imports", "test")


def run_task(task: Task) -> bool:
    """Run every command of a task; return True if all succeeded.

    Example:
        run_task(TASKS["lint"])
    """
    ok = True
    for command in task.commands():
        print(f"\n==> [{task.name}] {' '.join(command)}", flush=True)
        started = time.perf_counter()
        completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
        elapsed = time.perf_counter() - started
        status = "ok" if completed.returncode == 0 else f"FAILED (exit {completed.returncode})"
        print(f"<== [{task.name}] {status} in {elapsed:.1f}s", flush=True)
        ok = ok and completed.returncode == 0
    return ok


def run_many(names: Sequence[str]) -> int:
    """Run tasks in order, continue past failures, and print a summary.

    Returns the process exit code: 0 if every task passed, 1 otherwise.

    Example:
        run_many(["lint", "typecheck"])
    """
    results = {name: run_task(TASKS[name]) for name in names}
    print("\nSummary:")
    for name, passed in results.items():
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
    return 0 if all(results.values()) else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and run the requested tasks.

    Example:
        main(["check"])
    """
    choices = [*TASKS, "check"]
    epilog = "\n".join(f"  {t.name:<17} {t.help}" for t in TASKS.values())
    epilog += f"\n  {'check':<17} {' + '.join(CHECK_SEQUENCE)} (what CI runs)"
    parser = argparse.ArgumentParser(
        prog="dev.py",
        description="PaccaAssureTAF dev/CI tasks (ADR-0014).",
        epilog=f"tasks:\n{epilog}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("tasks", nargs="+", choices=choices, metavar="task", help="task(s) to run")
    args = parser.parse_args(argv)
    names: list[str] = []
    for name in args.tasks:
        names.extend(CHECK_SEQUENCE if name == "check" else (name,))
    return run_many(names)


if __name__ == "__main__":
    sys.exit(main())
