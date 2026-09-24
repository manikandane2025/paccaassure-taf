# paccaassure_taf.web

Modern web driver on Playwright (sync API): `WebPage`, `WebComponent`, sessions, evidence.

**Status:** empty skeleton (Phase 0). Built in **Phase 2** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `WebPage` (route, title, `go()`)
- `WebComponent`
- `WebSession` / `DriverFactory`
- network mock helpers

## Layer
- May import: elements, data, evidence, results, core.
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- One Browser per worker, one BrowserContext per scenario.
- Auto-wait only; never sleep.
- Traces retained on failure only; screenshots masked.

## How to extend
- New browser capability: extend `WebConfig`, keep it typed; add a sandbox scenario.

## Read first
DRIVERS.md (Web), ADR-0001 · root `CLAUDE.md` hard rules.
