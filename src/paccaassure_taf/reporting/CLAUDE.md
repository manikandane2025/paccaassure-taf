# paccaassure_taf.reporting

Builds the single self-contained HTML report and summary.md/json from `run.json` (+ history snapshot).

**Status:** empty skeleton (Phase 0). Built in **Phase 3** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `pataf report build/open`
- report panels (`paccaassure_taf.report_panels`)
- `_ui/` built template

## Layer
- May import: history, results, core (post-run stack).
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Offline, no CDN, works from a zipped folder.
- Never imports drivers, bdd or evidence capture.

## How to extend
- New report tab: implement a report panel plugin fed by result metadata.

## Read first
REPORTING.md §3, §7 · root `CLAUDE.md` hard rules.
