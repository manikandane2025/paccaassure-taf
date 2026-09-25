# Status and session handoff

> Read first in every new session. Keep under 80 lines. Update at every checkpoint.

**Phase:** 0 and 1 **done and merged into `develop`** (local `--no-ff` merges, 2026-09-25; not pushed). **Next: sandbox (Phases 2–5 subset), then Phase 2.** The sandbox must be complete before Phase 2.
**Branching (from now on):** each phase branches from `develop` and merges back `--no-ff` at its checkpoint. Next branch: `feature/sandbox` from `develop`. The user pushes; the agent never pushes.
**CI is last priority (user):** it has not run on GitHub. Don't spend effort on it until asked.

## Open items (owner: user)
- **Licensing tier split** (ADR-0010 open item): which features are core vs licensed extras is a pending business decision. `Entitlement` holds candidates only; **JSP may move to core**. Don't gate any feature until decided.

## Where things stand (local, Windows, Python 3.12.3)
| Check (`uv run python scripts/dev.py <task>`) | Result |
|---|---|
| lint, format-check, typecheck (mypy `--strict`), imports (7 contracts) | all clean |
| test (unit + docstring examples) | 310 passed |
| coverage (gate ≥ 90% on `core`) | 98% line+branch |
| licenses / audit / secrets | 0 violations / no known vulns / no leaks |
Core API summary: `src/paccaassure_taf/core/CLAUDE.md`. CLI: `pataf config show [--resolved]` = `python -m paccaassure_taf config show`.
Phase 1 review follow-ups done: ADR-0015 accepted; `core.runtime.apply_config()` applies `masking:`/`logging:` config at CLI startup (was not wired); learned masking values bounded (`masking.max_learned_values`, default 10,000, oldest-first; secrets pinned); Phase 2 has a masking performance check.

## ADRs and decisions
- ADR-0013 importers (Proposed) · ADR-0014 tool-agnostic CI · ADR-0015 own config loader with provenance (Accepted).
- Licenses: MIT, MIT-0, BSD-2/3, 0BSD, ISC, Apache-2.0, PSF, MPL-2.0; SPDX `OR` = any allowed; PostgreSQL via pg8000.
- Exit codes: 0 gate passed · 1 breached · 2 config/framework · 3 sink (opt-in); default gate = zero failures.
- `World[S]` + per-pack alias; multi-pack rule finalized in Phase 2 (ADR-0002 amendment 1).
- Synthetic credentials contain `Northwind` (`.gitleaks.toml`). License signer never ships; production key in Phase 11.
- Commit rules: small conventional commits with Co-Authored-By trailer; never push, force, or rewrite history.

## Next: sandbox — only what Phases 2–5 need (BUILD_PLAN "Sandbox split")
Stack: FastAPI API; Vite+Preact SPA behind nginx; Postgres 16 (`northwind` + `pataf_history`). Sandbox Python: ruff + standard mypy. Ports on 127.0.0.1: web **8081**, API **8083**, Postgres **5433** (8082 reserved for JSP). Synthetic data only (IDs like `NWH-M000123`; SSN-shaped values only in 9xx). Generated files with `newline="\n"`.
1. `feat(sandbox): add postgres with synthetic Northwind Health seed`
2. `feat(sandbox): add Northwind Health JSON API with OpenAPI` — auth/token, members (filters, paging), claims (201/409/422), plans, health, admin reset, `delay_ms`
3. `feat(sandbox): add Northwind Health web app` — login/roles, search (labels, Status select, `data-testid` table, paging), detail (tabs, dialog), edit form, CSV download, new-tab link
4. `build(sandbox): add dev.py sandbox tasks` — `sandbox-up/sandbox-smoke/sandbox-down`, sandbox license check
5. `docs: CHANGELOG, BUILD_PLAN and STATUS`
Stop at the checkpoint: report `docker compose up --wait` health + one smoke probe per app; merge `feature/sandbox` into `develop`.
**Moved to Phase 6 prerequisites:** the Tomcat JSP app (spec in BUILD_PLAN Phase 6).
Then Phase 2 (results model, elements, web, typed BDD, runner v1, `pataf doctor`, masking perf check).

## Environment quirks (this dev machine)
- **uv PATH:** shims `C:\Users\manikandane\bin\uv` (bash) and `uv.cmd` (cmd/PowerShell) forward to the winget install.
- **Blocked `.exe` launchers:** endpoint security blocks unsigned console-script launchers (`.venv\Scripts`, pre-commit cache). Always `python -m …` / `python -c …`. `ruff.exe` (signed) works.
- Don't use `sed` or heredoc-embedded Python for text containing backslashes (Windows paths, regexes); use the Edit tool.
- **PowerShell 5.1** is the user's shell (no `&&`); documented commands are cross-shell. `.gitattributes` keeps LF.
- Docker Desktop 27 (Linux engine); the pre-commit gitleaks hook needs Docker running.
