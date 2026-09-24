# Build plan (greenfield)

Each phase ends with a PR, green CI, updated docs/catalog, and the listed acceptance criteria met. Do not skip ahead.

## Phase 0 — Harvest and skeleton
- Fill `REFERENCE_FRAMEWORK_NOTES.md`.
- uv workspace, `src/paccaassure_taf` packages as empty modules with nested `CLAUDE.md`; pyproject with mypy/ruff/import-linter contracts (ARCHITECTURE §3); pre-commit; license allow-list check (SPDX `OR` aware); `scripts/dev.py` task runner; CI as a thin GitHub Actions adapter (lint + type + unit + licenses) per ADR-0014.
- Unit tests: a package import smoke test (every package imports, has a docstring and `__all__`), so the unit job has real tests from day one.
- `sandbox/compose.yaml` (Northwind Health, synthetic data): web app (FastAPI-backed Vite+Preact SPA behind nginx: login, search, table, detail, form), Tomcat 9 JSP app (frameset, postback form with Struts-style token, popup, generated-id table), FastAPI JSON API with OpenAPI, Postgres 16 with separate `northwind` (app data) and `pataf_history` DBs. Sandbox Python uses ruff + standard mypy (not `--strict`).
- ✅ mypy, ruff, lint-imports, license check pass; sandbox apps serve.

## Phase 1 — Core
- Layered typed config + `pataf config show`; SecretRef + env/Key Vault providers; structlog with masking; `Sensitive[T]` (in `core.masking`); errors; `wait.until`; plugin registry (incl. `ConnectionProvider`); license verification module (entry-point only, test keys).
- Exemption from hard rule 10: no runner exists yet, so Phase 1 features ship unit tests, docs and CHANGELOG but no sandbox e2e scenario or catalog regen.
- ✅ ≥ 90% unit coverage on core; masking proven; actionable config errors; expired license degrades gracefully.

## Phase 2 — Results model + elements + web + typed BDD
- `paccaassure_taf.results`: event and aggregate models, JSON Schema export, event writer, merger, `run.json`.
- `By`, typed elements (emit sub-action events), `expect`, `WebPage`/`WebComponent`, `Table[T]`.
- `paccaassure_taf.bdd`: typed decorators, `World[S]` (finalize the multi-pack scenario-store combination rule; amend ADR-0002), annotation-driven parse types, `Table[Model]` with `${…}` scenario references, hooks writing events, `w.evidence.record` → `StepResult.outputs`.
- Runner v1: `pataf run`, `--dry-run`, tags, env; `summary.md/json`.
- ✅ 10 sandbox web scenarios produce valid `run.json` (schema-validated); wrong element action fails mypy (should-fail test); dry-run resolves all steps.

## Phase 3 — Report UI v1
- `report-ui/` (TS strict, Vite, single-file build), generated TS types from JSON Schema, Overview / Tests / Test detail / Failures views, evidence viewer, white-label theme, `pataf report build/open`, shard merge.
- ✅ Report for the sandbox run opens offline from a zipped folder; 20k synthetic tests open < 3 s; Vitest + Playwright smoke on the report pass; schema→TS types freshness check in CI.

## Phase 4 — API + DB + files
- `ApiClient`, `Endpoint[Req, Resp]`, auth providers, OpenAPI contract check; `Query[Row]` for Oracle/MySQL-MariaDB/SQL Server/PostgreSQL; `ConnectionProvider` hook; file readers; **field-mapping comparator + report Field mapping panel** (DRIVERS Files, REPORTING §3). API/DB exchanges recorded as sub-actions + masked evidence.
- ✅ API + DB (sandbox Postgres `northwind`) + CSV + fixed-width mapping scenarios pass; exchanges and field mappings visible in report.

## Phase 5 — History + trends + gates
- `paccaassure_taf.history`: SQLAlchemy models, Alembic migrations, SQLite + Postgres (+ SQL Server) backends, ingest, `history.json` rolling mode, `vw_*` views, Python analytics with parity tests, export to Parquet/CSV.
- Report Trends + Traceability views, per-test sparkline; `paccaassure_taf.gates` using baselines and flaky scores; quarantine.
- ✅ 30 synthetic runs ingested; trends, flaky, new/regressed/fixed correct against fixtures in both SQL and Python; gates drive exit codes.

## Phase 6 — JSP driver
- Frames, postback, session recovery, popups, `ServletClient` with token extraction, locator lint.
- ✅ JSP sandbox scenarios pass including frameset + token form + popup.

## Phase 7 — Desktop driver
- ADR-0004 spike; `DesktopSession`, `DesktopScreen`, grid/tree/menu elements; `pataf doctor` desktop checks.
- ✅ Scenarios pass on a Windows agent against a sample desktop app; same element API as web; results/evidence identical in shape.

## Phase 8 — Scale and execution
- Parallel workers + CI sharding (ADR-0006), data reservation, retries/flaky attempts, runner image, Azure/Jenkins/GitHub pipeline templates (thin adapters over `pataf`, ADR-0014); Azure Pipelines / Jenkins adapters for core's own CI.
- ✅ 200-scenario suite in 4 shards → one merged report + one history run.

## Phase 9 — Sinks
- ADO (REST Test Runs, test points, attachments, summary, optional deduped bugs), Xray, Zephyr Scale, Power BI (direct-SQL docs + `bi/powerbi/` data dictionary & DAX, file export, push dataset), Teams, webhook, blob evidence sink; `pataf tms check`.
- ✅ Results visible in a test ADO project Tests tab and Jira sandbox; re-publish idempotent; Power BI Desktop connects to sandbox Postgres views and shows pass-rate and flaky trends.

## Phase 10 — Layering, templates, AI context
- Surface registry + `@overrides`, step rebind rules, `pataf lint overrides`; `examples/app-pack-demo` + `examples/variant-demo`; copier templates; `pataf catalog`, `pataf ai sync`, `_ai/` packaging; validate every `.claude/commands` recipe.
- ✅ A fresh Claude Code session in `examples/variant-demo`, given only "add a scenario that verifies X", produces passing, lint-clean code without reading core source.

## Phase 11 — Productization and 1.0
- Security review, sensitive-data scanner on results/evidence/history, performance targets, SBOM + signed artifacts, docs site (mkdocs-material), customer onboarding guide, Selenium/Java migration guide, license tooling, release 1.0.0.
