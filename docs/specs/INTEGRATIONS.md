# Integrations spec: CI/CD and test management

Reporting, history, trends and all result sinks (ADO, Jira, Power BI, Teams) are specified in `REPORTING.md`. This file covers execution environments and TMS linking.

## Execution modes (one CLI, four contexts)
| Mode | How | Notes |
|---|---|---|
| Local one-click | `pataf run --env qa --tags @smoke --open` | builds and opens the HTML report |
| Scheduled | CI scheduled pipeline using the same command | nightly regression per variant |
| Container | `docker run <registry>/paccaassure-taf-runner:<ver> pataf run ...` | Python + Playwright browsers; non-root; no Java/Node needed |
| CI gate | pipeline template stage on PR / release | gates decide pass/fail |
Desktop suites run on self-hosted **Windows** agents with Appium as a service.

## Pipeline templates (`pipelines/`)
- **Azure Pipelines**: `pataf-run.yml` (params: app, variant, env, tags, workers, shards), `pataf-post.yml` (merge → report → history ingest → gates → sinks), `pataf-release-pack.yml` (build/test/publish an app pack wheel). Sharding via `strategy: parallel` + `--shard i/N`; the post job merges shards.
- **Jenkins**: shared-library style Jenkinsfile with the same stages.
- **GitHub Actions**: reference workflow (for customers on GitHub).
- Each template publishes the report folder as an artifact and writes `summary.md` to the native CI summary.

## TMS linking (tags)
- `@tms:ADO-<id>`, `@tms:JIRA-<KEY>`, `@req:<id>`, `@id:<stable-test-id>`.
- `pataf tms check`: scenarios without TMS ids; TMS test cases with no automation; stale links. Output is also a report tab.
- Publishing to ADO Test Plans / Xray / Zephyr is done by sinks (REPORTING.md §5), after the run, idempotently.

## Secrets in CI
Workload identity / service connections → `kv://` SecretRefs; no secret values in pipeline YAML.

## Retries and flakiness
Scenario-level retry only for `@retryable` (default 0). Retries are recorded as attempts and the test is marked `flaky` if it passes after failing; history computes flaky scores across runs; quarantine list in config.

## Observability (optional)
OpenTelemetry spans per run/scenario/step when enabled; structured JSON logs with run/test/step correlation ids.
