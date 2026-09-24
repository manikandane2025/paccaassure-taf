# paccaassure_taf.results

The public result contract: event and aggregate models, JSON Schema export, event writer, merger.

**Status:** empty skeleton (Phase 0). Built in **Phase 2** — see `docs/BUILD_PLAN.md`.

## Planned public API
- events (`RunStarted` … `RunFinished`)
- `RunResult`, `TestResult`, `StepResult`, `FailureInfo`
- event writer (JSONL per worker)
- merger → `run.json`

## Layer
- May import: core.
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Public contract (hard rule 8): additive changes only within a major version.
- Every event is masked before it is written.
- Generated schema/TS types must never be stale.

## How to extend
- Use the `/change-result-schema` recipe for any model change.

## Read first
REPORTING.md §1, ADR-0011 · root `CLAUDE.md` hard rules.
