# Status and session handoff

> Read first in every new session. Keep under 80 lines. Update at every checkpoint.

**Phase:** 1 — Core, **in progress** (user decision 2026-09-24: Phase 1 before the sandbox; sandbox must finish before Phase 2 — BUILD_PLAN).
**Branch:** `feature/phase-1-core`, stacked on `feature/phase-0-skeleton` (pushed; Phase 0 last commit `da9ccbd`). See `git log` for Phase 1 progress.
**CI is last priority (user):** it has not run on GitHub (no PR yet). Don't spend effort on it until asked.

## Checkpoint 1 results (all local, Windows, Python 3.12.3)
| Task (`uv run python scripts/dev.py <task>`) | Result |
|---|---|
| lint, format-check | ruff clean |
| typecheck | mypy `--strict` clean (src, scripts, tests, stubs) |
| imports | 7/7 import-linter contracts kept; each contract proven to break on an injected violation |
| test | 70 passed |
| licenses | 130 distributions, 0 violations (ISC/0BSD now allowed) |
| audit | pip-audit: no known vulnerabilities |
| hooks | 16/16 pre-commit hooks pass |
| secrets | gitleaks (Docker) over full history: no leaks |
| lowest-direct floors | typecheck + tests pass at declared minimums (scratch copy) |
| CI workflow | actionlint 1.7.12 clean |

## Deviations → decisions recorded
- CI is tool-agnostic: all checks are `scripts/dev.py` tasks; `.github/workflows/ci.yml` is a thin adapter → **ADR-0014** (Accepted).
- External perf/security tool results (k6/ZAP/JMeter) via importer plugins, never bundled (k6 is AGPL) → **ADR-0013** (Proposed, build later).
- Python tools run via `python -m` (blocked `.exe` launchers); pre-commit hooks all `repo: local`; gitleaks via Docker → CODING_STANDARDS, customer-onboarding TEMPLATE.
- Added import-linter contract 5 (runtime ↛ post-run) → ARCHITECTURE §3.
- Own SPDX evaluator instead of pip-licenses → PRODUCT §3.

## Decisions made (Phase 0 review + checkpoint 1)
- Licenses: allow MIT, MIT-0, BSD-2/3, 0BSD, ISC, Apache-2.0, PSF, MPL-2.0; SPDX `OR` = any allowed; no (L)GPL/AGPL. PostgreSQL via **pg8000**, never psycopg (ADR-0010 amendments 1–2).
- Exit codes decided by the gate: 0 passed · 1 breached · 2 config/framework · 3 sink (opt-in); default gate = zero failures (REPORTING §6).
- `World[S]` generic + per-pack alias; multi-pack combination rule finalized in Phase 2 (ADR-0002 amendment 1).
- Sandbox stack: FastAPI API; Vite+Preact SPA behind nginx; Tomcat 9 JSP (Maven in multi-stage Docker); Postgres 16 with `northwind` + `pataf_history` DBs. Sandbox Python: ruff + standard mypy (not strict).
- Deps: floor + next-major cap (0.x → `<1`), `uv.lock` committed, lowest-direct CI job, matrix 3.12/3.13 × Windows/Linux. Build backend hatchling. LICENSE is a TODO-LEGAL placeholder.
- Branching: `main` / `develop` / `feature/*` from `develop`. Line endings LF (`*.ps1` CRLF).
- Commit rules: agent may `git commit` locally (conventional, small, with Co-Authored-By trailer); **never push, force, or rewrite history** — the user pushes.

## Next: Checkpoint 2 — sandbox (BUILD_PLAN Phase 0)
Ports on 127.0.0.1: web **8081**, JSP **8082**, API **8083**, Postgres **5433**. Synthetic data only (IDs like `NWH-M000123`; SSN-shaped values only in the never-issued 9xx range). Write generated files with `newline="\n"`.
Planned commits:
1. `feat(sandbox): add postgres with synthetic Northwind Health seed` — deterministic Faker seed, `northwind` schema + `pataf_history` DB.
2. `feat(sandbox): add Northwind Health JSON API with OpenAPI` — auth/token, members (filters, paging), claims (201/409/422), plans, health, admin reset, `delay_ms`; OpenAPI snapshot.
3. `feat(sandbox): add Northwind Health web app` — login/roles, search (labels, Status select, `data-testid` table, paging), detail (tabs, dialog), edit form (validation, date, upload, toast), CSV download, new-tab link.
4. `feat(sandbox): add Tomcat JSP legacy app` — login + JSESSIONID + short timeout, frameset `top>nav|content` + iframe, token postback (Struts-named TOKEN + CSRF), ISO-8859-1 page, `j_id` table, popup write-back, alert/confirm, servlet for `ServletClient`.
5. `ci: add sandbox health-check job` — `dev.py sandbox-up/sandbox-smoke/sandbox-down`, separate sandbox license check.
6. `docs: CHANGELOG, BUILD_PLAN and STATUS for checkpoint 2`.
Stop at Checkpoint 2: report `docker compose up --wait` health + one smoke probe per app.

## Environment quirks (this dev machine)
- **uv PATH:** winget install at `%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_…\uv.exe`. The VS Code-inherited PATH predated it, so shims `C:\Users\manikandane\bin\uv` (bash) and `uv.cmd` (cmd/PowerShell) forward to it (created 2026-09-24).
- Don't use `sed` replacements containing Windows paths (`\U`, `\a` are escapes there); use the Edit tool.
- **Blocked `.exe` launchers:** endpoint security blocks unsigned console-script launchers in `.venv\Scripts` and pre-commit's cache ("Access is denied"). Always `python -m …` / `python -c …`. `ruff.exe` (signed) works.
- **PowerShell 5.1** is the user's shell: no `&&`. All documented commands are cross-shell.
- `core.autocrlf=true` globally; `.gitattributes` keeps the repo LF.
- Docker Desktop 27 (Linux engine) running; gitleaks and actionlint images are pulled.
