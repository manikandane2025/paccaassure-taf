Add a framework (paccaassure-taf-core) capability: $ARGUMENTS

1. Read ARCHITECTURE.md, the relevant spec, and ADRs. If the design changes a decision, write an ADR first.
2. Write a 5–10 line plan: public API, layer, plugin point, config keys, tests.
3. Implement with mypy --strict; keep core product-agnostic.
4. Add: unit tests, a sandbox scenario, docs/spec update, nested CLAUDE.md update, CHANGELOG entry, catalog regen.
5. Run full checks, one command per line (cross-shell): `uv run python scripts/dev.py check`, then `uv run pataf lint`, then `uv run pataf catalog --check` (the `pataf` commands exist from Phase 2).
