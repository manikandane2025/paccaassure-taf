# paccaassure_taf.core

Foundation: typed config, secrets, structured logging, masking, waits, errors, plugin registry, license check.

**Status:** built in Phase 1 (98% line+branch coverage). Import from the submodules below.

## Public API
| Module | Use |
|---|---|
| `core.errors` | `PatafError(what, cause=, fix=)` + `ConfigError`, `SecretError`, `PluginError`, `LicenseError`, `WaitTimeoutError`, `LocatorError`, `ExpectationError` (an `AssertionError`), `DataError`, `IntegrationError`; `ExitCode` 0/1/2/3 |
| `core.masking` | `Sensitive[T]` field marker; `Masker().mask(obj)` / `.scrub(text)` / `.register(value)`; `default_masker()` |
| `core.log` | `configure_logging(level=, fmt=, stream=)`, `get_logger(name)`, `correlation(run_id=, test_key=, step=)` |
| `core.wait` | `wait.until(probe, description=, timeout=, interval=, accept=, ignoring=)` — the only way to wait |
| `core.plugins` | `PluginRegistry[Base](PluginKind.X, Base)`: entry points `paccaassure_taf.plugins`, names `<kind>.<name>` |
| `core.config` | `load_config(root, env=, app_files=, overrides=, environ=)` → `ResolvedConfig` (`.config: PatafConfig`, `.source_of(key)`, `.render()`) |
| `core.secrets` | `SecretRef` (`env://`, `kv://`, `hcv://`, `file://`), `SecretProvider`, `SecretResolver`, `build_secret_resolver(...)` |
| `core.secrets_azure` | `KeyVaultSecretProvider` (extra `secrets-azure`, entry point `secret_provider.kv`) |
| `core.license` | `check_license(path, today=, public_keys=)` → `LicenseStatus` (`.state`, `.entitles(Entitlement.X)`, `.banner`) — never raises |

## Layer
- May import: third-party only — no other `paccaassure_taf` package. Never playwright/appium/behave.
- Enforced by import-linter (ARCHITECTURE §3).

## Invariants
- `core/config/environment.py` is the only reader of `os.environ`; everything else takes an `environ` mapping.
- Everything written or logged goes through a `Masker` first (ADR-0009). Resolved secrets and learned `Sensitive` values are scrubbed from all later text. Never echo a rejected input value for a sensitive key.
- Errors are actionable: `what` + likely `cause` + `fix`.
- No `time.sleep`: use `wait.until`. License checks only at CLI entry points, never mid-scenario; expiry degrades, never breaks a run.
- Plugins: duplicate names fail loudly; plugin bases may be abstract (pass the type parameter explicitly).
- Synthetic test credentials contain `Northwind` (gitleaks allowlist).

## How to extend
- New secret backend: subclass `SecretProvider` (no-arg constructor), register entry point `secret_provider.<scheme>`.
- New config setting: add a field to a `_Section` model in `config/model.py` (keep `extra="forbid"`), plus a test.
- New plugin kind: add to `PluginKind`, document in ARCHITECTURE §5.

## Read first
CONFIG_SECRETS_DATA.md, ADR-0009, ADR-0010, ADR-0015 · root `CLAUDE.md` hard rules.
