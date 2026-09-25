# paccaassure_taf.runner

The `pataf` CLI (Typer): run, report, history, gates, sinks, doctor, catalog, lint, config, ai, license.

**Status:** empty skeleton (Phase 0). Built in **Phase 2** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `pataf` console script (added when the first command exists)

## Layer
- May import: everything below it in both stacks (top of the runtime and post-run contracts).
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Thin: commands delegate to packages; no business logic here.
- License check only at entry points.
- Exit codes per REPORTING §6.

## How to extend
- New command: add a Typer sub-app; document it in CLAUDE.md commands when stable.

## Read first
ARCHITECTURE.md §4, INTEGRATIONS.md · root `CLAUDE.md` hard rules.
