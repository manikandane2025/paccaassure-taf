# Changelog

All notable changes to `paccaassure-taf-core` are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/) (public API, result schema and `vw_*` views are contracts).

## [Unreleased]

### Added
- Reference framework harvest notes (`docs/REFERENCE_FRAMEWORK_NOTES.md`).
- ADR-0013 external result importers (Proposed) and ADR-0014 tool-agnostic CI (Accepted).
- Repository hygiene: `.gitattributes` (LF, CRLF for Windows scripts), `.editorconfig`, `.gitignore`, `.python-version`.

### Changed
- Specs updated after the Phase 0 review: import-linter contracts, `World[S]`, exit codes decided by the gate, pg8000 for PostgreSQL, SPDX-aware license policy, `StepResult.outputs`, `FailureInfo.category = auth`, `@risk` tag, cross-shell commands.
