# paccaassure_taf.desktop

Windows desktop driver on Appium 2: `DesktopSession`, `DesktopScreen`, grid/tree/menu elements.

**Status:** empty skeleton (Phase 0). Built in **Phase 7** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `DesktopSession`
- `DesktopScreen` (`window_title`)

## Layer
- May import: elements, data, evidence, results, core.
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Same element API as web.
- Runs only on Windows agents; never in Linux Docker.
- Locator priority: AutomationId → AccessibilityId/Name → class+name → xpath with `reason=`.

## How to extend
- Driver choice is pending the ADR-0004 spike; do not hardcode a Windows driver.

## Read first
DRIVERS.md (Desktop), ADR-0004 · root `CLAUDE.md` hard rules.
