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


def _test() -> list[list[str]]:
    return [python_module("pytest", "tests/unit")]


TASKS: dict[str, Task] = {
    task.name: task
    for task in (
        Task("lint", "ruff lint (no fixes)", _lint),
        Task("format-check", "ruff format --check", _format_check),
        Task("format", "apply ruff fixes and formatting", _format),
        Task("typecheck", "mypy --strict (config in pyproject.toml)", _typecheck),
        Task("test", "unit tests", _test),
    )
}

# Aggregate run by CI and before every PR. Order: fastest feedback first.
CHECK_SEQUENCE: tuple[str, ...] = ("lint", "format-check", "typecheck", "test")


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
    epilog = "\n".join(f"  {t.name:<14} {t.help}" for t in TASKS.values())
    epilog += f"\n  {'check':<14} {' + '.join(CHECK_SEQUENCE)} (what CI runs)"
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
