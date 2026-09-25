"""Claude Code PostToolUse hook: ruff-fix and format the one Python file just edited.

Reads the hook payload (JSON on stdin), and if the edited file is Python inside
this repo, runs ``ruff check --fix`` and ``ruff format`` on that file only.
Never fails the agent's edit: all problems are reported, then exit 0.
Full checks (mypy, import-linter) run in pre-commit and CI (AI_NATIVE §4).

Example (what Claude Code sends on stdin):
    {"tool_name": "Edit", "tool_input": {"file_path": "C:/repo/src/paccaassure_taf/core/x.py"}}
"""

from __future__ import annotations

import json
import subprocess
import sys
import sysconfig
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_SUFFIXES = {".py", ".pyi"}


def edited_file(payload: str) -> Path | None:
    """Return the edited Python file inside the repo, or None.

    Example:
        edited_file('{"tool_input": {"file_path": "README.md"}}')  # -> None
    """
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    raw = data.get("tool_input", {}).get("file_path") if isinstance(data, dict) else None
    if not isinstance(raw, str):
        return None
    path = Path(raw).resolve()
    if path.suffix not in PYTHON_SUFFIXES or not path.is_file() or not path.is_relative_to(REPO_ROOT):
        return None
    return path


def main() -> int:
    """Run ruff on the edited file; always return 0.

    Example:
        main()
    """
    path = edited_file(sys.stdin.read())
    if path is None:
        return 0
    ruff = Path(sysconfig.get_path("scripts")) / ("ruff.exe" if sys.platform == "win32" else "ruff")
    for args in (["check", "--fix", "--quiet", "--force-exclude"], ["format", "--quiet", "--force-exclude"]):
        try:
            completed = subprocess.run(
                [str(ruff), *args, str(path)], cwd=REPO_ROOT, capture_output=True, text=True, check=False
            )
        except OSError as error:  # ruff missing or blocked: report, never block the edit
            print(f"post_edit hook: could not run ruff ({error})", file=sys.stderr)
            return 0
        if completed.stdout.strip():
            print(completed.stdout.strip(), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
