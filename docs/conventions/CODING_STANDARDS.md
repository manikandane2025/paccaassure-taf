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
- Control: `@wip` (never in CI), `@retryable`, `@serial`, `@db-write`, `@a11y`, `@har`, `@known-issue:<id>`
- Env constraints: `@env:uat` / `@not-env:prod`

## Git
Conventional commits; branch `feature/<ticket>-<slug>`; PR template requires: spec updated? catalog regenerated? tests added? CHANGELOG?
