# Sandbox: Northwind Health

The apps that PaccaAssureTAF's own e2e scenarios run against. **Northwind Health** is a fictitious company.
All data is synthetic, and nothing here ships to customers.

```text
uv run python scripts/dev.py sandbox-up       # build + start + wait for healthy + smoke probe per app
uv run python scripts/dev.py sandbox-smoke    # probe again
uv run python scripts/dev.py sandbox-down     # stop and remove containers and the data volume
docker compose -f sandbox/compose.yaml up -d --build --wait    # plain compose also works
```

## Ports and settings
Every port binds to `127.0.0.1` only. Settings live in `sandbox/.env`, which is gitignored and local to your machine. `dev.py sandbox-up` creates it from [`env.example`](env.example) if it is missing. If a port clashes, change it in `sandbox/.env`. `NWH_SANDBOX_*` is used (not `PATAF_*`) because `pataf` rejects unknown `PATAF_*` variables.

| Service | Default | Variable |
|---|---|---|
| Postgres 16 (`northwind`, `pataf_history`) | 15433 | `NWH_SANDBOX_DB_PORT` |

## Postgres
Init scripts are in `postgres/initdb/` and run once, on an empty volume. `dev.py sandbox-down` removes the volume, so the next `up` reseeds from scratch.

| Role | Password (synthetic) | Access |
|---|---|---|
| `northwind_app` | `pw-Northwind-app` | owns `northwind` |
| `northwind_ro` | `pw-Northwind-readonly` | `SELECT` on `plans`, `members`, `claims` (never credentials) |
| `pataf_history` | `pw-Northwind-history` | owns `pataf_history` (empty; Phase 5 migrations create tables) |
| `postgres` | `pw-Northwind-postgres` | superuser |

`northwind` tables: `plans`, `members`, `claims`, `app_users`, `api_clients`. `nwh_reset_seed()` restores the deterministic seed (same rows every time).

### Seed rules
- Member ids `NWH-M000001`…`NWH-M000250`; claim ids `NWH-C0000001`…; plan codes `NWH-P001`…`NWH-P006`.
- SSN-shaped values only in the never-issued `9xx-xx-xxxx` range, phones in `555-01xx`, e-mail under `members.northwind.example`.
- Synthetic credentials contain `Northwind` (the gitleaks allowlist).

### Well-known rows
| Row | Use |
|---|---|
| `NWH-M000123` Ava Thompson, ACTIVE, Gold Plus (`NWH-P003`) | 5 claims, one per status (`SUBMITTED`, `IN_REVIEW`, `APPROVED`, `DENIED`, `PAID`) |
| `NWH-M000150` Seán O'Brien-Nuñez | accents + apostrophe (encoding, quoting) |
| `NWH-M000200` / `NWH-M000033` / `NWH-M000047` | INACTIVE / SUSPENDED / PENDING |
| Last name `Garcia` | exactly 10 members (paging with small page sizes) |
| `NWH-P006` Legacy Bronze | inactive plan |

Totals: 250 members (226 ACTIVE, 12 INACTIVE, 7 SUSPENDED, 5 PENDING), 377 claims.
