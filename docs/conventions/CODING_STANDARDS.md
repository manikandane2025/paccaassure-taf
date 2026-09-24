# Coding standards

## Python
- Python 3.12+, `from __future__ import annotations` not needed; use PEP 695 generics where they help readability.
- mypy `--strict`; no `# type: ignore` without an error code and a reason comment.
- ruff: rules E, F, I, B, UP, N, SIM, PL (selected), ANN, D (google style), T20 (no print), plus custom bans: `time.sleep`, `print`, `os.environ[...]` outside `paccaassure_taf.core.config`.
- Public API exported via `__all__`; private modules prefixed `_`.
- Errors: raise `PatafError` subclasses (`ConfigError`, `LocatorError`, `ExpectationError`, `DataError`, `IntegrationError`) with actionable messages ("what failed, likely cause, how to fix").

## Naming
| Thing | Pattern | Example |
|---|---|---|
| Web/JSP page | `<Noun>Page` | `MemberSearchPage` |
| Desktop screen | `<Noun>Screen` | `ClaimEntryScreen` |
| Component | `<Noun>` + `Component` base | `HeaderNav` |
| Endpoint | verb+noun | `GetMember`, `CreateClaim` |
| API client | `<Service>Api` | `MemberApi` |
| Flow class | `<Domain>Flows` | `EligibilityFlows` |
| Element attribute | snake_case noun, + role suffix for buttons | `member_id`, `search_btn` |
| Feature file | `<domain>/<capability>.feature` | `eligibility/member_search.feature` |
| SQL file | `<entity>_by_<key>.sql` | `eligibility_by_member.sql` |

## Step vocabulary
- Given = state ("an active adult member exists"), When = one user intent ("the eligibility worker searches for that member"), Then = observable outcome ("the results show").
- Actors are `UserRole` values; objects are data refs; no UI words (click, button, field) in Gherkin.
- Present tense, third person, no "I".

## Tag taxonomy (validated by `pataf lint tags`)
- Scope: `@app:<slug>` `@variant:<slug>`
- Suite: `@smoke` `@regression` `@release` `@sanity`
- Layer: `@web` `@jsp` `@api` `@desktop` `@db` `@file`
- Traceability: `@tms:ADO-<id>` | `@tms:JIRA-<KEY>`, `@req:<id>`, `@id:<stable-test-id>` (keeps history across renames)
- Ownership: `@owner:<team>` (report + history dimension)
- Risk: `@risk:low` | `@risk:medium` | `@risk:high` (report filter + history dimension; enables risk-based selection such as `--tags "@risk:high"`)
- Control: `@wip` (never in CI), `@retryable`, `@serial`, `@db-write`, `@a11y`, `@har`, `@known-issue:<id>`
- Env constraints: `@env:uat` / `@not-env:prod`

## Cross-platform (Windows is a first-class dev platform)
- Open every text file with `encoding="utf-8"` (ruff `PLW1514`); use `pathlib`, never string path concatenation.
- Generated filenames: no `:`; slugify + short hash (avoids reserved names like `CON`/`NUL` and MAX_PATH issues). Run ids look like `20260924T101500Z-ab12cd`.
- Line endings are LF in the repo (`.gitattributes`), except `*.ps1`/`*.cmd`/`*.bat` (CRLF).
- Dev and CI tasks are Python (`scripts/dev.py`), never bash-only or PowerShell-only one-liners.

## Git
Conventional commits. Branches: `main` (released), `develop` (integration), `feature/<ticket>-<slug>` from `develop` (ADR-0003). PR template requires: spec updated? catalog regenerated? tests added? CHANGELOG?
