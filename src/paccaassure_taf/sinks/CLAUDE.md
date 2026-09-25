# paccaassure_taf.sinks

Result sinks (ADO, Jira/Xray/Zephyr, Power BI, Teams, webhook) behind `ResultSink`.

**Status:** empty skeleton (Phase 0). Built in **Phase 9** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `ResultSink.publish(run, ctx) -> SinkReport`
- `Notifier`

## Layer
- May import: history, results, core (post-run stack).
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Idempotent and retry-safe.
- A sink failure never changes the test outcome (exit 3 only when opted in).
- Payloads are masked; consume `RunResult` only.

## How to extend
- Use the `/new-sink` recipe; register under `paccaassure_taf.sinks`; add an install extra.

## Read first
REPORTING.md §5, ADR-0007 · root `CLAUDE.md` hard rules.
