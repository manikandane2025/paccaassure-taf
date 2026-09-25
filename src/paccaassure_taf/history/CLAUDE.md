# paccaassure_taf.history

History store: SQLAlchemy models, Alembic migrations, ingest, `vw_*` views, analytics, export.

**Status:** empty skeleton (Phase 0). Built in **Phase 5** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `HistoryStore` protocol
- SQLite / PostgreSQL (pg8000) / SQL Server backends
- `history.analytics`

## Layer
- May import: results, core (post-run stack).
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- `vw_*` views are the public BI contract (ADR-0012).
- SQL and Python analytics stay in parity (contract tests).
- Ingest is idempotent by `run_id`.

## How to extend
- New backend: implement `HistoryStore`, register under `paccaassure_taf.history_backends`.

## Read first
REPORTING.md §4, ADR-0012 · root `CLAUDE.md` hard rules.
