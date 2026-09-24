# Config, secrets and test data

## Config
- Typed with pydantic-settings: `PatafConfig` (core) extended by app-pack and variant config models via plugin.
- Files: YAML; env overlays in `envs/<env>.yaml`; `Env` is an enum declared per variant suite (`local, dev, qa, uat, stage`).
- `pataf config show --resolved` prints merged config with value source; secrets shown as `***`.
- Invalid config fails fast at startup with a precise pydantic error (exit code 3).

## Secrets
- Only `SecretRef` strings in config: `kv://<vault>/<name>`, `env://VAR`, `hcv://<path>#<key>`, `file://` (local dev only, blocked in CI).
- Providers: Azure Key Vault (azure-identity DefaultAzureCredential), HashiCorp Vault, env. Cached per process.
- Credentials per role: `users.<role>.username / password` refs; `UserRole` enum per product.

## Test data
- Synthetic by default (factories + Faker with fixed seeds per scenario for reproducibility).
- Data profiles per env (`data/profiles/uat.yaml`) keyed by stable names (`active_adult`) → typed models.
- `DataProvider` plugins: DB lookup ("find an active member matching X"), API seeding, ServletClient seeding, and a future central test-data service ("Test data client" in slides).
- Data reservation for parallel runs: `w.data.reserve(Member, "active_adult")` returns an exclusive record (lock file locally, DB/table or service in CI).
- Cleanup via registered teardown callbacks in reverse order.

## PHI and masking
- `Sensitive[T]` marker type; masking applied when result events and evidence are written (so reports, history and sinks only ever see masked values); Playwright trace text redaction post-processor where feasible, and trace retention limited to failures in non-local envs.
- Screenshots of PHI screens in shared envs: `evidence.screenshots: failures_only | blurred_fields` (blur elements marked `sensitive=True`).
- Nothing real in Git: pre-commit gitleaks + PHI regex hook; CI scans evidence bundles before publishing.
