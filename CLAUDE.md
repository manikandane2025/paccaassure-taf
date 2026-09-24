# PaccaAssureTAF — enterprise test automation platform (core)

> Root context for coding agents (Claude Code, Copilot, Cursor) and humans. Read this first, every session.
> Product name: **PaccaAssureTAF** (PaccaAssure Test Automation Framework). Use these identifiers exactly:
>
> | Thing | Name |
> |---|---|
> | Product / docs / report branding | PaccaAssureTAF |
> | Core distribution (wheel) | `paccaassure-taf-core` |
> | Python import root | `paccaassure_taf` |
> | CLI command | `pataf` |
> | Env var prefix | `PATAF_` |
> | Config files | `pataf.app.yaml`, `pataf.variant.yaml` |
> | Synced context dir in consumer repos | `.pataf/context/` |
> | Class name prefix (when needed) | `Pataf` (e.g. `PatafConfig`, `PatafError`) |
> | Runner image / report UI | `paccaassure-taf-runner`, `paccaassure-taf-report-ui` |
> | Entry-point groups | `paccaassure_taf.plugins`, `paccaassure_taf.sinks`, … |

## Mission
Build a **commercial, customer-agnostic** test automation product that we license to multiple enterprise customers. It must:
1. Ship as a versioned core package (`paccaassure-taf-core`) that customers build on. They never fork it.
2. Support a three-tier model any customer can map onto their organization:
   - **Core** (us).
   - **App packs**, one per application under test, owned by the customer's app/product teams.
   - **Variant suites**, per deployment, client, region, state, or tenant. These are owned by the teams who test that variant and extend app packs without forking them.
3. Automate **modern web (Playwright), legacy JSP/Servlet web, REST APIs, Windows desktop (Appium), DB and files** through one strongly typed authoring model.
4. Produce results with **our own reporting engine**: an event model, a self-contained HTML report, a history store with trend analytics, and pluggable sinks for ADO, Jira, Power BI and more. Allure and JUnit are **not used**.
5. Be **AI-native**. Every PaccaAssureTAF repo (core, app pack, variant suite) carries the context an agent needs to script or extend correctly without outside explanation.

## Stack (non-negotiable unless an ADR changes it)
- Python 3.12+, uv, Behave, Playwright (sync API), Appium 2 + Appium-Python-Client, httpx, pydantic v2 + pydantic-settings, SQLAlchemy 2 + Alembic (history store), python-oracledb / PyMySQL / pyodbc, structlog, Typer, pytest (framework unit tests only), mypy `--strict`, ruff, import-linter, pre-commit, copier, Docker.
- Report UI: TypeScript + Vite, built to a **single self-contained HTML template**. Its types are generated from the Python result models.
- **Every dependency must carry a commercial-friendly license** (MIT/BSD/Apache-2.0/PSF/MPL-2.0). No GPL/AGPL. This is enforced in CI (ADR-0010).

## Where things are
| Need | Read |
|---|---|
| Product principles, licensing, packaging, white-label | `docs/PRODUCT.md` |
| Layers, packages, dependency rules | `docs/architecture/ARCHITECTURE.md` |
| Why a decision was made | `docs/architecture/adr/` |
| **How scripts are written (typed style)** | `docs/specs/TYPED_AUTHORING.md` (the most important spec) |
| **Results, report UI, history, trends, sinks** | `docs/specs/REPORTING.md` |
| Web / JSP / API / Desktop / DB / file drivers | `docs/specs/DRIVERS.md` |
| App packs vs variant suites, overrides | `docs/specs/LAYERING.md` |
| CI/CD, ADO, Jira, notifications | `docs/specs/INTEGRATIONS.md` |
| Config, secrets, test data, sensitive-data masking | `docs/specs/CONFIG_SECRETS_DATA.md` |
| How the AI-native context system works | `docs/specs/AI_NATIVE.md` |
| Code style, naming, tags | `docs/conventions/CODING_STANDARDS.md` |
| Vocabulary | `docs/GLOSSARY.md` |
| What to build next | `docs/BUILD_PLAN.md` |
| Harvest notes from the reference repo | `docs/REFERENCE_FRAMEWORK_NOTES.md` |

## Hard rules (violations fail review)
1. **Customer-agnostic core.** No customer names, apps, domains, URLs, or business rules in `paccaassure-taf-core` code, tests, examples, or docs. Examples use the fictitious demo company **Northwind Health**.
2. **Typed everything.** `mypy --strict` passes with zero unexplained ignores in `src/`. No `Any` in public APIs. No raw strings where an enum or model exists.
3. **Layer direction:** `bdd → flows → pages/screens/endpoints → elements/drivers → core`. Never upward. Enforced by import-linter.
4. **Steps are one-liners** that call a flow, a page, or `expect`. No locators, waits, or branching logic in steps.
5. **No sleeps.** `time.sleep` is banned. Use auto-wait or `paccaassure_taf.core.wait.until(...)`.
6. **No secrets or sensitive data in Git or unmasked artifacts.** Use `SecretRef` for secrets and `Sensitive[...]` for fields such as PII/PHI/PCI. Masking happens before anything is written to disk or sent to a sink.
7. **Reuse before create.** Search `docs/catalog/` (generated) first. Duplicate step phrasing fails `pataf lint steps`.
8. **The result event schema is a public contract.** It is versioned. Changes are additive within a major version, and every change updates the JSON Schema, the TS types, and the history migrations together.
9. **Every public class and function has a docstring with a usage example.** Catalogs are generated from them.
10. **Each feature ships complete:** unit tests, a sandbox e2e scenario, a docs update, a catalog regen, and a CHANGELOG entry.
11. **Public API follows SemVer.** A breaking change needs a major bump, a note in `docs/migrations/`, and one minor version of deprecation warnings first.

## Commands
```bash
uv sync                                   # install workspace
uv run pataf doctor                     # env check: browsers, Appium, DB drivers, history store, license
uv run pataf run --app demo --variant demo --env local --tags @smoke
uv run pataf run --dry-run              # resolve every step, no execution
uv run pataf report build --run latest  # build self-contained HTML report
uv run pataf report open                # open latest report
uv run pataf history ingest --run latest   # push results to history store
uv run pataf history trends --last 30   # CLI trend summary
uv run pataf catalog                    # regenerate docs/catalog/*
uv run pataf lint                       # steps + features + tags + locators + overrides
uv run pytest tests/unit
uv run mypy src && uv run ruff check . && uv run lint-imports
(cd report-ui && npm ci && npm run build) # report UI template
docker compose -f sandbox/compose.yaml up -d
```

## Working agreement for agents
- Work phase by phase from `docs/BUILD_PLAN.md`. Don't start a phase until the previous phase's acceptance criteria pass.
- Before writing code in a new area, read its spec and state your plan in 5–10 lines.
- If a spec is ambiguous or wrong, update the spec or add an ADR in the same change. Docs are the source of truth.
- Use small, conventional commits.
- When two designs compete, choose the one that is easier for a less-experienced scripter **and** an AI agent to use correctly.
