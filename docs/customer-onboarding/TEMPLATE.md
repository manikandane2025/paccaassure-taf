# Customer onboarding: <Customer>

Kept in the **customer's** repos (copy this template there), never in paccaassure-taf-core.

## Terminology map
| Customer term | PaccaAssureTAF term |
|---|---|
| | app pack |
| | variant suite |

## App packs
| App pack | Technology (web/JSP/API/desktop/DB) | Owner team | Variants consuming it |
|---|---|---|---|

## Variant suites
| Variant suite | App packs | Owner team | TMS project |
|---|---|---|---|

## Environments, secrets, TMS, history store, sinks
- Envs:
- Secret store:
- TMS (ADO project / Jira project):
- History store (SQLite / Postgres / SQL Server):
- Sinks enabled (ADO, Jira, Power BI, Teams):

## Locked-down Windows endpoints
Managed Windows machines (AppLocker / WDAC / EDR) often block **unsigned executables in user-writable paths** — including the console-script launchers that uv and pre-commit create (`.venv\Scripts\*.exe`, `%USERPROFILE%\.cache\pre-commit\…`). Symptom: `Access is denied (os error 5)` / `PermissionError: [WinError 5]` when running a tool that is installed. Native signed binaries (e.g. `ruff.exe`, `uv.exe`) are usually unaffected.
- Run Python tools as modules: `uv run python -m pytest`, `uv run python -m pre_commit install`, `uv run python -m mypy`. PaccaAssureTAF's own tasks (`scripts/dev.py`, pipeline templates) already do this.
- pre-commit hooks: use `repo: local` hooks that run from the locked uv environment (`python -m pre_commit_hooks.<hook>`), not remote hook repos that build their own virtualenvs.
- Secret scanning: run gitleaks from its pinned Docker image when its binary (or Go, for pre-commit) cannot be installed; CI runs the full-history scan.
- `pataf doctor` reports this condition (planned, Phase 2).
- Record here: blocked? (yes/no) · policy owner · exception request raised? ·

| Check | Result |
|---|---|
| Console-script launchers runnable (`uv run pytest --version`) | |
| `python -m` entry points runnable | |
| Docker available for gitleaks / sandbox | |
| Playwright bundled Chromium downloads and launches (`uv run python -m playwright install chromium`); else use `browser: msedge` | |

## Migration waves
| Wave | Scope | Legacy stack | Classification counts (Reuse/Refactor/Rebuild/Retire/Blocked) |
|---|---|---|---|
