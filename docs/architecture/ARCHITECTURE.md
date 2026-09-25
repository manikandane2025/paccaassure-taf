# Architecture

## 1. Three-tier model (customer-neutral)
```
variant suites  (per deployment / client / state / tenant)   ← customer's variant QA teams
   depends on ▼ (pinned versions)
app packs       (one per application under test)             ← customer's app/product teams
   depends on ▼ (pinned versions)
paccaassure-taf-core    (this repo — our product)                    ← us
```
- Dependencies flow **down only**. A variant suite may depend on several app packs.
- App packs publish to the customer's private feed; they pin `paccaassure-taf-core>=1.4,<2`.
- This repo contains **copier templates** to scaffold app packs and variant suites, and **examples/** (Northwind Health demo) proving the layering end to end against the sandbox apps.

## 2. Repository layout (target)
```
paccaassure-taf-core/
├── CLAUDE.md  AGENTS.md  README.md  CHANGELOG.md  LICENSE (commercial)  pyproject.toml (uv workspace)
├── src/paccaassure_taf/
│   ├── core/          # config, secrets, logging, masking, wait, errors, plugin registry, license check
│   ├── elements/      # driver-neutral typed elements + By
│   ├── web/  jsp/  api/  desktop/  data/     # drivers (see specs/DRIVERS.md)
│   ├── flows/  bdd/   # Flow base; typed steps, World, parse types, hooks
│   ├── results/       # result event & aggregate models (public contract), event writer, merger
│   ├── evidence/      # capture + masking + evidence sinks
│   ├── reporting/     # HTML report builder, summary.md/json, _ui/ (built template)
│   ├── history/       # HistoryStore, SQLAlchemy models, Alembic migrations, analytics, export
│   ├── gates/         # quality gates
│   ├── sinks/         # ado/, jira/, powerbi/, teams/, webhook/ — plugins behind ResultSink
│   ├── runner/        # CLI (Typer): run, report, history, gates, sinks, doctor, catalog, lint, config, ai, license
│   └── _ai/           # context shipped inside the wheel (specs/AI_NATIVE.md)
├── report-ui/         # TypeScript report app → single-file template
├── schemas/results/v1 # generated JSON Schema (public contract)
├── bi/powerbi/        # view docs, data dictionary, DAX snippets
├── tests/unit  tests/integration  tests/contract (schema + SQL/Python analytics parity)
├── sandbox/           # docker compose: Northwind web app, Tomcat JSP app, API app, Postgres (northwind + pataf_history DBs)
├── examples/app-pack-demo/  examples/variant-demo/
├── templates/app-pack/  templates/variant-suite/   # copier
├── pipelines/azure/  pipelines/jenkins/  pipelines/github/   # CUSTOMER-facing templates (Phase 8)
├── scripts/dev.py     # cross-shell dev/CI task runner — the only thing CI calls (ADR-0014)
├── .github/workflows/ci.yml   # core's OWN CI: thin adapter over scripts/dev.py (ADR-0014)
├── stubs/             # typed stubs for untyped third-party packages (e.g. behave)
├── docker/            # runner image
└── docs/
```
The root `pyproject.toml` is both the core package and the uv workspace root; `examples/*` join as workspace members in Phase 10.
Every `src/paccaassure_taf/<pkg>/` has a short `CLAUDE.md` (purpose, public API, invariants, how to extend).

## 3. Logical layers (inside every test)
| Layer | Owns | May import |
|---|---|---|
| `features/*.feature` | business intent, tags, TMS ids | — |
| steps (bdd) | Gherkin ↔ typed call, one line | flows, surfaces, data models |
| flows | multi-surface business tasks | surfaces, data |
| pages / screens / endpoints | surface models, typed elements | elements, drivers |
| elements + drivers | technology interaction; emit sub-action events | core, results |
| results / evidence | recording | core |
| core | config, secrets, logging, masking (incl. `Sensitive[T]`), waits, errors, plugins | 3rd party only |

### Package contracts (import-linter, `pyproject.toml`)
Higher layers may import lower ones, never the reverse. `a | b` = independent siblings (may not import each other).

**Contract 1 — runtime stack** (what runs inside a scenario):
```
runner
bdd
flows
jsp                      # builds on web
web | api | desktop
elements | data          # data = models, db, files (surfaces import data models)
evidence
results
core
```
**Contract 2 — post-run stack** (after the run, from `run.json`):
```
runner
sinks | gates | reporting
history                  # reporting embeds trend snapshots; gates use baselines; sinks dedupe by signature
results
core
```
**Contract 3 — forbidden:** `reporting`, `history`, `gates`, `sinks` must not import `bdd`, `flows`, `web`, `jsp`, `api`, `desktop`, `elements`, `data`, `evidence`.
**Contract 4 — forbidden externals:** `core` and `results` must not import `playwright`, `appium`, `behave`; only `web` and `jsp` may import `playwright`; only `desktop` may import `appium`; only `bdd` and `runner` may import `behave`.
**Contract 5 — forbidden:** runtime packages (`core` … `bdd`) must not import `reporting`, `history`, `gates`, `sinks`. (Contracts 1 and 2 each constrain only the packages they list, so without this a runtime→post-run import such as `elements → history` would pass.)
`tests/unit/test_import_contracts.py` proves each contract type fails on a deliberate violation.
`Sensitive[T]` lives in `core.masking` (masking must see it) and is re-exported by `paccaassure_taf.data` for authors.

## 4. Runtime flow
1. `pataf run` verifies license (entry point only), resolves layered config, selects features by tags.
2. Shards features across workers (ADR-0006); each worker runs Behave with PaccaAssureTAF hooks and writes `events-<worker>.jsonl`.
3. `World` lazily creates sessions (web, jsp, api, desktop, db). Drivers emit sub-action events; failures capture masked evidence.
4. After the run: merge → `run.json` → HTML report → history ingest (if configured) → gates → sinks.
Each post-run stage is also a standalone CLI command so CI can split them into separate steps.

## 5. Extension points (entry-point groups)
`paccaassure_taf.plugins` (ElementType, ParseType, DriverFactory, AuthProvider, SecretProvider, DataProvider, ConnectionProvider — access brokers / just-in-time DB credentials run before a DB connect), `paccaassure_taf.sinks` (ResultSink, Notifier), `paccaassure_taf.evidence_sinks`, `paccaassure_taf.history_backends`, `paccaassure_taf.report_panels` (custom report tabs fed by extra result metadata), `paccaassure_taf.importers` (Proposed, ADR-0013: external tool results → `TestResult`). Core never hardcodes a vendor.

## 6. Non-functional targets
- Framework overhead per scenario < 300 ms excluding app time; event writing < 5% of runtime.
- Dry-run of 5,000 scenarios < 60 s. Report for 20k tests opens < 3 s.
- History ingest of a 10k-test run < 30 s on Postgres.
- Flake budget < 2% on sandbox suite across 20 CI runs.
- Zero unmasked sensitive data in results, evidence, report, history, or sink payloads (scanner in CI).
