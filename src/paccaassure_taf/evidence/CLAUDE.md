# paccaassure_taf.evidence

Evidence capture (screenshots, traces, HAR, API/DB exchanges, logs), masking and evidence sinks.

**Status:** empty skeleton (Phase 0). Built in **Phase 2** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `Evidence` capture API (`w.evidence.capture`, `w.evidence.record`)
- `EvidenceSink` protocol

## Layer
- May import: results, core.
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Evidence is masked/blurred before it is stored.
- Referenced from results by relative path + sha256 + size + mime.

## How to extend
- New evidence store: implement `EvidenceSink`, register under `paccaassure_taf.evidence_sinks`.

## Read first
REPORTING.md §2, CONFIG_SECRETS_DATA.md · root `CLAUDE.md` hard rules.
