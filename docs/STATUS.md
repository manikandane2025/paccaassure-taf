# Status and session handoff

> Read first in every new session. Keep under 80 lines. Update at every checkpoint.

**Phase:** 0 and 1 **done and merged into `develop`** (2026-09-25). **Sandbox done on `feature/sandbox`** (2026-09-26, 5 commits, not merged, not pushed): at its checkpoint, awaiting user review. **Next:** user OK → merge `feature/sandbox` into `develop` (`--no-ff`) → Phase 2 on `feature/phase-2-…` from `develop`.
**Branching:** each phase branches from `develop` and merges back `--no-ff` at its checkpoint. The user pushes; the agent never pushes.
**CI is last priority (user):** it has not run on GitHub. Don't spend effort on it until asked.

## Open items (owner: user)
- **Licensing tier split** (ADR-0010 open item): which features are core vs licensed extras is a pending business decision. `Entitlement` holds candidates only; **JSP may move to core**. Don't gate any feature until decided.

## Where things stand (local, Windows, Python 3.12.3)
| Check (`uv run python scripts/dev.py <task>`) | Result |
|---|---|
| lint, format-check, typecheck (mypy `--strict`), imports (7 contracts) | all clean |
| test (unit + docstring examples) | 324 passed |
| coverage (gate ≥ 90% on `core`) | 98% line+branch |
| licenses / audit / secrets | 0 violations / no known vulns / no leaks |
| sandbox-up / sandbox-smoke | 3/3 containers healthy (fresh volume, ~31 s); 4/4 probes pass |
| sandbox-typecheck / sandbox-licenses | clean / 23 Python + 62 npm, 0 violations |
Core API summary: `src/paccaassure_taf/core/CLAUDE.md`. CLI: `pataf config show [--resolved]` = `python -m paccaassure_taf config show`.
Phase 1 review follow-ups done: ADR-0015 accepted; `core.runtime.apply_config()` applies `masking:`/`logging:` config at CLI startup (was not wired); learned masking values bounded (`masking.max_learned_values`, default 10,000, oldest-first; secrets pinned); Phase 2 has a masking performance check.

## ADRs and decisions
- ADR-0013 importers (Proposed) · ADR-0014 tool-agnostic CI · ADR-0015 own config loader with provenance (Accepted).
- Licenses: MIT, MIT-0, BSD-2/3, 0BSD, ISC, Apache-2.0, PSF, MPL-2.0; SPDX `OR` = any allowed; PostgreSQL via pg8000.
- Exit codes: 0 gate passed · 1 breached · 2 config/framework · 3 sink (opt-in); default gate = zero failures.
- `World[S]` + per-pack alias; multi-pack rule finalized in Phase 2 (ADR-0002 amendment 1).
- Synthetic credentials contain `Northwind` (`.gitleaks.toml`). License signer never ships; production key in Phase 11.
- Commit rules: small conventional commits with Co-Authored-By trailer; never push, force, or rewrite history.

## Sandbox (done; details in `sandbox/README.md`, agent notes in `sandbox/CLAUDE.md`)
Ports on 127.0.0.1 (**changed from 8081/8083/5433**, which are taken on this machine): web **18081**, API **18083**, Postgres **15433**, **18082** reserved for JSP. Configurable in `sandbox/.env` (gitignored; `dev.py sandbox-up` creates it from committed `sandbox/env.example`; `compose.yaml` has the same `${NWH_SANDBOX_*:-default}`s). Variable prefix `NWH_SANDBOX_`: `pataf` rejects unknown `PATAF_*` env vars.
- Postgres 16: `northwind` (owner `northwind_app`; `northwind_ro` read-only, no credentials tables) + empty `pataf_history`. Seed = `nwh_reset_seed()` (deterministic: 6 plans, 250 members, 377 claims; well-known `NWH-M000123`). Passwords `pw-Northwind-*`.
- API (FastAPI + pg8000, own `sandbox/api/uv.lock`): token (password/client_credentials), members, CSV export, claims 201/409/422, plans (public), health, admin reset, `delay_ms`, RFC 9457 problems. Accounts: `admin`/`examiner`/`viewer`/`locked`, password `pw-Northwind-<user>`.
- Web (Vite 8 + Preact + TS 7, nginx proxies `/api/`): login, search, paging, tabs, dialog, edit form, CSV download, new tab. Verified end to end with Playwright (Edge channel).
- Commits: postgres seed · JSON API · web app · `dev.py` sandbox tasks · docs.
**Phase 6 prerequisite (not built):** the Tomcat JSP app (spec in BUILD_PLAN Phase 6), port 18082.
**Phase 2 next:** results model, elements, web, typed BDD, runner v1, `pataf doctor`, masking perf check. The 10 sandbox web scenarios run against http://127.0.0.1:18081.

## Environment quirks (this dev machine)
- **uv PATH:** shims `C:\Users\manikandane\bin\uv` (bash) and `uv.cmd` (cmd/PowerShell) forward to the winget install.
- **Blocked `.exe` launchers:** endpoint security blocks unsigned console-script launchers (`.venv\Scripts`, pre-commit cache). Always `python -m …` / `python -c …`. `ruff.exe` (signed) works.
- Don't use `sed` or heredoc-embedded Python for text containing backslashes (Windows paths, regexes); use the Edit tool.
- **PowerShell 5.1** is the user's shell (no `&&`); documented commands are cross-shell. `.gitattributes` keeps LF.
- Docker Desktop 27 (Linux engine); the pre-commit gitleaks hook needs Docker running.
- **Playwright browsers not installed** (`playwright install` never run). Edge works via `channel="msedge"`; `pataf doctor` (Phase 2) should report missing browsers.
- **`sandbox/.env` is agent-read-denied** (`.claude/settings.json`), and so is `.env.*`: edit `sandbox/env.example`, never read the user's `.env`.
- Ports already taken here: 3000, 5433 (native Postgres service), 5434, 8000, 8002, 8081. Check with `netstat -ano | findstr :<port>`.
