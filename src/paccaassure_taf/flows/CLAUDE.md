# paccaassure_taf.flows

`Flow` base for multi-surface business tasks with typed inputs and outputs.

**Status:** empty skeleton (Phase 0). Built in **Phase 2** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `Flow` (with `self.app` resolving surfaces through the override registry)

## Layer
- May import: jsp, web, api, desktop, elements, data, evidence, results, core.
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Flows orchestrate surfaces; they never hold locators.
- Surfaces resolve through the SurfaceRegistry.

## How to extend
- New flow: subclass `Flow` in the app pack, one method per business task, docstring with example.

## Read first
TYPED_AUTHORING.md §6, LAYERING.md · root `CLAUDE.md` hard rules.
