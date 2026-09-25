# paccaassure_taf.bdd

Typed BDD layer over Behave: decorators, `World[S]`, annotation-driven parse types, `Table[T]`, hooks.

**Status:** empty skeleton (Phase 0). Built in **Phase 2** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `given` / `when` / `then`
- `World[S]`
- `Table[T]`
- hooks writing result events

## Layer
- May import: flows, jsp, web, api, desktop, elements, data, evidence, results, core.
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Steps are one-liners (hard rule 4).
- Patterns use bare `{name}`; types come from annotations.
- Duplicate/overlapping patterns fail `pataf lint steps`.

## How to extend
- New parse type: register a `ParseType` plugin; it then works in any annotated step.

## Read first
TYPED_AUTHORING.md §8–9, ADR-0002 · root `CLAUDE.md` hard rules.
