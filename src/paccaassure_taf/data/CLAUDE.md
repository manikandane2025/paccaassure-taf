# paccaassure_taf.data

Test data: pydantic `TestData` models, factories, profiles, reservation; DB (`Query[Row]`) and file readers.

**Status:** empty skeleton (Phase 0). Built in **Phase 4** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `TestData`, `factory`, `Sensitive` (re-exported from `core.masking`)
- `Query[Row]`, `Mutation`
- file readers + field-mapping comparator
- `DataProvider`, `ConnectionProvider` plugins

## Layer
- May import: evidence, results, core.
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Synthetic data only; never real PII/PHI.
- SQL lives in `.sql` files with named binds; read-only by default.
- PostgreSQL via pg8000 only (never LGPL psycopg).

## How to extend
- New DB/broker: implement `ConnectionProvider`; new file format: add a typed reader.

## Read first
TYPED_AUTHORING.md §5, DRIVERS.md (DB, Files), CONFIG_SECRETS_DATA.md · root `CLAUDE.md` hard rules.
