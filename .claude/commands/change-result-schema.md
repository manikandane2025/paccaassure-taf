Change the result model / history schema: $ARGUMENTS

1. Read REPORTING.md §1 and §4, ADR-0011, ADR-0012. The result schema and `vw_*` views are public contracts.
2. Within a major version changes must be additive (new optional fields, new views/columns). Otherwise stop and propose an ADR.
3. Update together, in one change: pydantic models → `schemas/results/v1` export → `report-ui/src/generated` types → Alembic migration → views → Python analytics → parity tests → `bi/powerbi` data dictionary.
4. Bump `schema_version` minor; add fixtures for old and new versions; the report must still open old `run.json` files.
