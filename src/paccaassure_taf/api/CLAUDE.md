# paccaassure_taf.api

REST API driver on httpx: `ApiClient`, typed `Endpoint[Req, Resp]`, auth providers, contract checks.

**Status:** empty skeleton (Phase 0). Built in **Phase 4** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `ApiClient`
- `Endpoint[Req, Resp]` (`method: ClassVar[HttpMethod]`)
- `ApiResponse[Resp]` via `call_raw()`
- `AuthProvider` plugins

## Layer
- May import: elements, data, evidence, results, core.
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Retries only for idempotent methods.
- Request/response evidence is masked.
- Failures raise typed errors; never return `None`.

## How to extend
- New auth scheme: implement `AuthProvider`, register under `paccaassure_taf.plugins`.

## Read first
DRIVERS.md (API) · root `CLAUDE.md` hard rules.
