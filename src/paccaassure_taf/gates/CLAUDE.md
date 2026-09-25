# paccaassure_taf.gates

Quality gates: turn results + history into the run's exit code.

**Status:** empty skeleton (Phase 0). Built in **Phase 5** — see `docs/BUILD_PLAN.md`.

## Planned public API
- gate config model
- gate evaluation → exit code 0/1/2/3

## Layer
- May import: history, results, core (post-run stack).
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- The gate decides the exit code: 0 passed · 1 breached · 2 config/framework · 3 sink (opt-in).
- Default gate when none is configured: zero failures.
- Quarantined tests are reported but not gated.

## How to extend
- New rule: add a typed field to the gate config and a Python + fixture test.

## Read first
REPORTING.md §6 · root `CLAUDE.md` hard rules.
