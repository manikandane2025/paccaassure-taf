# paccaassure_taf.core

Foundation: typed config, secrets, structured logging, masking, waits, errors, plugin registry, license check.

**Status:** empty skeleton (Phase 0). Built in **Phase 1** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `PatafConfig` + layered loading
- `SecretRef`, `SecretProvider`
- `Sensitive[T]` (in `core.masking`)
- `wait.until(...)`
- `PatafError` hierarchy
- plugin registry (entry points)
- license verification

## Layer
- May import: third-party only — no other `paccaassure_taf` package.
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- The only place allowed to read the environment (`core/config/**`).
- Masking happens before anything is written or sent (ADR-0009).
- License checks run only at CLI entry points, never mid-scenario (ADR-0010).
- Never imports playwright, appium or behave.

## How to extend
- New secret backend: implement `SecretProvider`, register under `paccaassure_taf.plugins`.
- New config section: add a pydantic model; document it in config-reference.

## Read first
CONFIG_SECRETS_DATA.md, ADR-0009, ADR-0010 · root `CLAUDE.md` hard rules.
