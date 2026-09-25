# Changelog

All notable changes to `paccaassure-taf-core` are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/) (public API, result schema and `vw_*` views are contracts).

## [Unreleased]

### Added
- Reference framework harvest notes (`docs/REFERENCE_FRAMEWORK_NOTES.md`).
- ADR-0013 external result importers (Proposed) and ADR-0014 tool-agnostic CI (Accepted).
- Repository hygiene: `.gitattributes` (LF, CRLF for Windows scripts), `.editorconfig`, `.gitignore`, `.python-version`.
- uv project (`pyproject.toml`, `uv.lock`) with extras per PRODUCT §2; mypy `--strict`, ruff, pytest configuration.
- Package skeleton: 16 `paccaassure_taf` subpackages, each with a nested `CLAUDE.md`.
- Partial type stubs for behave (`stubs/behave`).
- Seven import-linter contracts (ARCHITECTURE §3) with violation tests.
- Unit tests: package smoke test, version, behave stubs, import contracts, license checker.
- SPDX-aware dependency license allow-list check (`scripts/check_licenses.py`, `scripts/license_policy.toml`).
- `scripts/dev.py` cross-shell task runner: lint, format, typecheck, imports, test, licenses, audit, hooks, secrets.
- pre-commit (all local hooks, gitleaks via Docker) and a per-file Claude Code PostToolUse hook.
- GitHub Actions CI as a thin adapter over `dev.py`: checks, unit-test matrix (Linux/Windows × 3.12/3.13), lowest-direct floors, licenses + vulnerability audit.
- `docs/STATUS.md` session handoff; locked-down Windows endpoint guidance in the customer onboarding template.

- **Phase 1 core** (`paccaassure_taf.core`): actionable `PatafError` hierarchy and `ExitCode`; `Sensitive[T]` + `Masker` (fields, SecretStr, sensitive keys, learned values, SSN/bearer/credential/card patterns); structlog logging with masking and correlation ids; `wait.until`; entry-point `PluginRegistry`; layered config with per-value provenance (`load_config`, `PatafConfig`); `SecretRef` + env/file/Azure Key Vault providers and `SecretResolver`; offline Ed25519 license verification.
- `pataf --version` and `pataf config show [--resolved]`, also as `python -m paccaassure_taf`.
- ADR-0015 config loader with provenance; `.gitleaks.toml` allowlisting synthetic `Northwind` credentials; `dev.py coverage` (>=90% on core) and doctests in `dev.py test`.

### Changed
- `pydantic-settings` removed (ADR-0015); floors raised to pydantic>=2.11 and typer>=0.26 after the lowest-direct check failed at the old floors; `cryptography` added.
- License allow-list adds ISC and 0BSD (ADR-0010 amendment 2); `shellingham` exception removed.
- Specs updated after the Phase 0 review: import-linter contracts, `World[S]`, exit codes decided by the gate, pg8000 for PostgreSQL, SPDX-aware license policy, `StepResult.outputs`, `FailureInfo.category = auth`, `@risk` tag, cross-shell commands.
