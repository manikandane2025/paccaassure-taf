# sandbox/ — Northwind Health apps for framework e2e scenarios

Docker Compose apps that the framework's own scenarios run against. They never ship. Human docs: [README.md](README.md).

## Invariants
- **Synthetic data only.** Fictitious names; SSN-shaped values only in `9xx`; phones `555-01xx`; e-mail `*.northwind.example`; credentials contain `Northwind` (gitleaks allowlist).
- **Deterministic seed.** `postgres/initdb/20-northwind-seed.sql` → `nwh_reset_seed()` is the single source of seed data (init and the API's `POST /admin/reset` both call it). If you change well-known rows, update README "Well-known rows".
- **Ports** bind to `127.0.0.1` and come from `sandbox/.env` via `${NWH_SANDBOX_*:-default}` in `compose.yaml`. Keep `env.example` and the compose defaults the same. Never use `PATAF_*` names here: `pataf` rejects unknown `PATAF_*` variables.
- Agents must not read `sandbox/.env` (it is local to the user; `.claude/settings.json` denies it). Edit `env.example` instead.
- Sandbox Python uses ruff (root config) + standard mypy (not `--strict`). Sandbox dependencies get their own license check (ADR-0010).
- Customer-agnostic like core (hard rule 1): Northwind Health only.
- Generated or text files use LF (`.gitattributes`); shell scripts run in Linux containers.
