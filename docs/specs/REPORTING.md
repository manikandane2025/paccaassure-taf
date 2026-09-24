# Reporting, history and trends spec

PaccaAssureTAF owns its results pipeline end-to-end. **No Allure, no JUnit.** Everything else (HTML report, trends, ADO, Jira, Power BI) is derived from one canonical, versioned result model.

```
runner hooks ──► events.jsonl (per worker) ──► merge ──► run.json (RunResult)
                                                          │
             ┌───────────────────────┬────────────────────┼─────────────────────┐
             ▼                       ▼                    ▼                     ▼
      HTML report builder     History store (SQL)    Quality gates        Sinks (plugins)
      single self-contained   SQLite / Postgres /    uses history for     ADO · Jira/Xray/Zephyr
      file, offline           SQL Server/Azure SQL   baselines & flaky    Power BI · Teams · webhook
             ▲                       │
             └── trend snapshot ─────┘  (last N runs embedded in report)
```

## 1. Result model (public contract)
Package: `paccaassure_taf.results`. Pydantic v2 models → exported JSON Schema (`schemas/results/v1/*.json`) → generated TypeScript types for the UI (`report-ui/src/generated/`). One source of truth; CI fails if generated artifacts are stale.

### Events (append-only, `results/<run-id>/events-<worker>.jsonl`)
`RunStarted`, `SuiteStarted` (feature), `TestStarted` (scenario / outline example), `StepStarted`, `StepFinished`, `Attachment`, `LogRecord` (sampled, masked), `TestFinished`, `SuiteFinished`, `RunFinished`. Every event has `schema_version`, `run_id`, `worker_id`, `ts` (UTC, monotonic seq), and is masked **before** being written.

Streaming events (not one big file at the end) means: crash-safe partial results, live progress in CLI, and a future live mode in PaccaAssureTAF Hub.

### Aggregates (`run.json`)
- `RunResult`: run id, project, app(s), variant, env, trigger (local/CI/schedule), CI metadata (provider, pipeline, build number, commit, branch, PR), tool versions (core, app packs, browsers, Appium driver), start/end, totals, gate outcome, license banner.
- `TestResult`: **stable `test_key`**, title, feature path, tags, TMS ids, requirement ids, layer(s), status (`passed|failed|broken|skipped|blocked|flaky`), attempts, duration, failure (`FailureInfo`), steps, attachments.
- `StepResult`: keyword, text, typed params (masked), status, duration, sub-actions (element actions and API calls recorded by drivers — "Clicked MemberSearchPage.search_btn"), attachments.
- `FailureInfo`: category (`assertion|locator|timeout|api|data|environment|framework`), message (masked), element/endpoint involved, stack (trimmed to user code), **failure signature** (hash of normalized message + category + element/endpoint + top user frame; volatile tokens like ids, numbers, timestamps stripped).
- Status semantics: `failed` = assertion/expectation failed (likely product or test bug); `broken` = error outside expectation (locator, timeout, env, exception); `flaky` = failed then passed on retry in this run.

### Test identity
`test_key = sha1(app + feature relative path + scenario title + example row key)`, overridable by `@id:<stable-id>` tag so renames keep history. `pataf lint` warns when a rename would break history without an `@id`.

## 2. Evidence
- Stored under `results/<run-id>/evidence/<test_key>/<attempt>/`: screenshots (masked/blurred per config), Playwright traces, desktop page-source, HAR, API request/response (masked), DB query + result summary, logs.
- Referenced from results by relative path + sha256 + size + mime.
- Retention policy per env; large binaries optionally uploaded to blob storage by an `EvidenceSink`, results keep the URL.

## 3. HTML report (`pataf report build`)
- **One self-contained HTML file** (`report.html`): UI bundle + run data (compressed JSON, embedded) + small evidence inline where under a size threshold; larger evidence linked relatively (`evidence/…`) so the folder zipped as a CI artifact just works. No server, no CDN, works offline and air-gapped.
- Views:
  1. **Overview** — status donut, totals, duration, gate result, environment & versions, top failure signatures, new/regressed/fixed vs baseline.
  2. **Tests** — tree by app → feature → scenario; filters (status, tag, layer, variant, TMS id, owner), search, sort by duration.
  3. **Test detail** — steps with timings, sub-actions, params, failure panel, evidence viewer (screenshot lightbox, trace download/open instructions, API exchange viewer, log viewer), history sparkline for this test.
  4. **Failures** — grouped by signature with counts and affected tests; category breakdown.
  5. **Trends** (when history available) — pass rate, duration, flaky rate over last N runs; top flaky; slowest; newly failing.
  6. **Traceability** — requirements/TMS ids → tests → latest status; uncovered TMS items (from `pataf tms check`).
- White-label theme from config; dark/light; keyboard accessible (WCAG 2.1 AA).
- Merge: `pataf report build --merge results/shard-*` combines shards into one run.
- Performance target: 20k tests report opens < 3 s on a laptop (virtualized lists, lazy evidence).
- Also emits `summary.md` (markdown summary for CI summaries/PR comments) and `summary.json` (compact metrics).

## 4. History store (`paccaassure_taf.history`)
- `HistoryStore` protocol; backends via SQLAlchemy 2: **SQLite** (local, single team, zero setup), **PostgreSQL** and **SQL Server/Azure SQL** (shared, recommended for Power BI). Alembic migrations shipped in the wheel; `pataf history migrate`.
- Ingest: `pataf history ingest --run <id>` (CI step after the run; idempotent by `run_id`). Optional auto-ingest at end of `pataf run`.
- No-DB mode for CI-only teams: `history.json` rolling file (last N runs, compact) carried between pipeline runs as an artifact; report builder and gates read it. Same analytics, limited depth.

### Schema (star schema; stable, documented, versioned)
Dimensions: `dim_project`, `dim_app`, `dim_variant`, `dim_env`, `dim_test` (test_key, title, feature, first_seen, last_seen, owner), `dim_tag` + `bridge_test_tag`, `dim_tms_item`, `dim_requirement`, `dim_failure_signature`, `dim_build` (CI metadata, versions), `dim_date`.
Facts: `fact_run` (one row per run), `fact_test_result` (one row per test per run, final attempt + attempt count), `fact_step_result` (optional, configurable — high volume), `fact_attempt` (for flaky analysis).
Retention: configurable per fact table; monthly rollup table `agg_test_month` for long horizons.

### Analytics (SQL views + Python API; the **public BI contract**)
| View | Purpose |
|---|---|
| `vw_run_summary` | per run: totals, pass rate, duration, gate result |
| `vw_test_trend` | per test per run: status, duration |
| `vw_flaky_tests` | flip rate & pass-on-retry rate over window (default last 20 runs); flaky score 0–1 |
| `vw_new_failures` | failing now, passed in baseline run |
| `vw_regressions` / `vw_fixed` | status transitions vs baseline |
| `vw_failure_signatures` | signature, first/last seen, occurrences, affected tests |
| `vw_duration_stats` | p50/p95/max per test, drift vs trailing average |
| `vw_stability_by_env` | pass rate by env/app/variant |
| `vw_traceability` | requirement/TMS item → tests → latest status |
| `vw_mttr` | mean time to repair for failing tests |
Baseline = previous run with same project/app/variant/env/branch (configurable: `baseline: last | last_on_main | tagged:<label>`).
The same computations exist in Python (`paccaassure_taf.history.analytics`) for report and gates, and are unit-tested against the SQL views for parity.

## 5. Sinks (plugins, entry-point group `paccaassure_taf.sinks`)
Protocol: `ResultSink.publish(run: RunResult, ctx: SinkContext) -> SinkReport` — idempotent, retry-safe, reports what it did; failures of a sink never change the test outcome (exit code 4 only if `sinks.fail_on_error: true`).

### Azure DevOps (`sinks-ado`)
- **Test Runs via REST API** (no JUnit file needed): create run (linked to build/release and optionally a Test Plan/Suite), add results with outcome, duration, error, stack (masked), associated Test Case (from `@tms:ADO-<id>`, updates test points), attachments (screenshots, trace zip, report link), complete run. Results appear in ADO "Tests" tab and Test Plans.
- Pipeline summary: `##vso[task.uploadsummary]summary.md`; report folder as pipeline artifact; optional "PaccaAssureTAF report" link in build tags.
- Optional: bug creation for **new** failure signatures only (dedup by signature stored in history), work item linking, automation status sync.
- Supports ADO Services and Server (API version configurable).

### Jira (`sinks-jira`)
- Xray (Cloud & DC): import executions using Xray JSON format generated from RunResult (not JUnit/Cucumber files).
- Zephyr Scale: create cycle + executions via REST.
- Plain Jira: comment/transition on linked issues; defect creation dedup by signature.

### Power BI (`sinks-powerbi`) — three supported patterns
1. **Recommended:** Power BI connects directly (Import or DirectQuery) to the shared history store (Postgres / SQL Server / Azure SQL) using the documented `vw_*` views. Nothing to push.
2. **File-based:** `pataf history export --format parquet|csv --since 90d --to <path|abfss://|sharepoint>` writes the star schema as partitioned files for Import mode / Fabric Lakehouse.
3. **Push:** Power BI REST push dataset for a small real-time tile set (run summary only; API limits apply).
- Ship `bi/powerbi/` with: view documentation, a data dictionary, recommended relationships/measures (DAX snippets), and later a `.pbit` template authored by a human.

### Others
Teams / Slack (cards from `summary.json`), email, generic webhook (signed HMAC), blob storage evidence sink, OpenTelemetry exporter.

## 6. Quality gates (read results + history)
Config: `min_pass_rate`, `max_new_failures`, `max_regressions`, `max_flaky_score`, `required_tags_passed`, `max_duration`, `quarantine` (known flaky tests excluded from gate but still reported). Exit codes: 0 pass · 1 failures within gate · 2 gate breached · 3 config/framework error · 4 sink error (opt-in).

## 7. Report UI engineering (`report-ui/`)
- TypeScript strict, Vite, a small framework (Preact or Solid) — no heavy UI kits; charts with a lightweight lib (uPlot or ECharts tree-shaken). License allow-list applies.
- Built output `dist/report-template.html` copied into `src/paccaassure_taf/reporting/_ui/` at build; Python injects data at a marker.
- Component tests (Vitest) + Playwright visual smoke of the report itself (dogfooding).
- Types imported only from `src/generated/` (from JSON Schema). No hand-written duplicates of result types.
