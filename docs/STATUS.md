# Status and session handoff

> Read first in every new session. Keep under 80 lines. Update at every checkpoint.

**Phase:** 1 — Core **done** (acceptance met 2026-09-24). **Next: sandbox (the remaining Phase 0 item), then Phase 2.** The sandbox must be complete before Phase 2 (user decision; BUILD_PLAN).
**Branches:** `feature/phase-1-core` (Phase 1, not pushed yet) is stacked on `feature/phase-0-skeleton` (pushed, last `da9ccbd`). Neither is merged; no PRs.
**CI is last priority (user):** it has not run on GitHub. Don't spend effort on it until asked.

## Phase 1 results (local, Windows, Python 3.12.3)
| Check (`uv run python scripts/dev.py <task>`) | Result |
|---|---|
| lint, format-check, typecheck (mypy `--strict`), imports (7 contracts) | all clean |
| test (unit + every docstring example) | 295 passed |
| coverage (gate ≥ 90% on `core`) | **98.4%** line+branch |
| licenses / audit / secrets | 0 violations / no known vulns / no leaks |
| lowest-direct floors (scratch copy) | typecheck + 295 tests pass |
Delivered: `core.errors`, `core.masking` (`Sensitive[T]`), `core.log`, `core.wait`, `core.plugins`, `core.config` (layered, provenance), `core.secrets` (+ `secrets_azure`), `core.license`; `pataf config show [--resolved]` / `python -m paccaassure_taf`. API summary: `src/paccaassure_taf/core/CLAUDE.md`.

## Findings fixed during Phase 1 (worth remembering)
- A plaintext password placed where a `SecretRef` belongs was echoed in the config error → validators never echo values; sensitive-key inputs hidden.
- Luhn alone masked ~10% of long numeric ids (run ids) → card masking also requires brand prefix + length.
- Config provenance: a section created by a later layer claimed its untouched siblings → only leaves carry sources.
- Declared floors were wrong (pydantic 2.10, typer 0.15) → raised to 2.11 / 0.26 after the lowest-direct run.

## ADRs and decisions
- ADR-0013 importers (Proposed) · ADR-0014 tool-agnostic CI · **ADR-0015 own config loader with provenance, pydantic-settings dropped (please confirm)**.
- Licenses: MIT, MIT-0, BSD-2/3, 0BSD, ISC, Apache-2.0, PSF, MPL-2.0; SPDX `OR` = any allowed; PostgreSQL via pg8000 (ADR-0010 amendments 1–2).
- Exit codes: 0 gate passed · 1 breached · 2 config/framework · 3 sink (opt-in); default gate = zero failures.
- `World[S]` + per-pack alias; multi-pack rule finalized in Phase 2 (ADR-0002 amendment 1).
- Synthetic credentials contain `Northwind` (`.gitleaks.toml` allowlist). License signer never ships; production public key added in Phase 11.
- Sandbox stack: FastAPI API; Vite+Preact SPA behind nginx; Tomcat 9 JSP (Maven in multi-stage Docker); Postgres 16 (`northwind` + `pataf_history`). Sandbox Python: ruff + standard mypy.
- Commit rules: agent commits locally (conventional, small, Co-Authored-By trailer); **never push, force, or rewrite history**.

## Next: sandbox (then Phase 2)
Ports on 127.0.0.1: web **8081**, JSP **8082**, API **8083**, Postgres **5433**. Synthetic data only (IDs like `NWH-M000123`; SSN-shaped values only in 9xx). Generated files with `newline="\n"`. Branch `feature/sandbox` from `feature/phase-1-core`.
1. `feat(sandbox): add postgres with synthetic Northwind Health seed`
2. `feat(sandbox): add Northwind Health JSON API with OpenAPI` — auth/token, members (filters, paging), claims (201/409/422), plans, health, admin reset, `delay_ms`
3. `feat(sandbox): add Northwind Health web app` — login/roles, search (labels, Status select, `data-testid` table, paging), detail (tabs, dialog), edit form, CSV download, new-tab link
4. `feat(sandbox): add Tomcat JSP legacy app` — JSESSIONID + short timeout, frameset `top>nav|content` + iframe, token postback (Struts TOKEN + CSRF), ISO-8859-1, `j_id` table, popup write-back, alert/confirm, servlet for `ServletClient`
5. `ci: add sandbox tasks` — `dev.py sandbox-up/sandbox-smoke/sandbox-down`, sandbox license check
6. `docs: CHANGELOG, BUILD_PLAN and STATUS`
Stop at the checkpoint: report `docker compose up --wait` health + one smoke probe per app.
Then Phase 2 (results model, elements, web, typed BDD, runner v1, `pataf doctor` with locked-down endpoint detection).

## Environment quirks (this dev machine)
- **uv PATH:** shims `C:\Users\manikandane\bin\uv` (bash) and `uv.cmd` (cmd/PowerShell) forward to the winget install (VS Code's inherited PATH predates it).
- **Blocked `.exe` launchers:** endpoint security blocks unsigned console-script launchers (`.venv\Scripts`, pre-commit cache). Always `python -m …` / `python -c …`. `ruff.exe` (signed) works.
- Don't use `sed` or heredoc-embedded Python for text containing backslashes (Windows paths, `\n` in code); use the Edit tool.
- **PowerShell 5.1** is the user's shell (no `&&`); documented commands are cross-shell. `core.autocrlf=true`; `.gitattributes` keeps LF.
- Docker Desktop 27 (Linux engine); gitleaks and actionlint images pulled. The pre-commit gitleaks hook needs Docker running.
