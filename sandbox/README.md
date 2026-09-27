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
| Web app (nginx + Vite/Preact SPA) | 18081 | `NWH_SANDBOX_WEB_PORT` |
| *(reserved: Tomcat JSP app, Phase 6)* | 18082 | `NWH_SANDBOX_JSP_PORT` |
| JSON API (FastAPI) | 18083 | `NWH_SANDBOX_API_PORT` |
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

## JSON API (`api/`)
FastAPI + pg8000, running at `http://127.0.0.1:18083`. The OpenAPI 3.1 document is at `/openapi.json`, and Swagger UI is at `/docs`.

| Endpoint | Auth | Notes |
|---|---|---|
| `GET /health` | public | `200 {"status":"ok","database":"ok"}`; `503` when the DB is down |
| `POST /auth/token` | public | JSON body. `{"username","password"}` (password grant) or `{"grant_type":"client_credentials","client_id","client_secret"}` → `{access_token, token_type, expires_in, role, display_name}`. Wrong credentials `401`, locked account `423` |
| `GET /auth/me` | any role | the caller's identity |
| `GET /plans`, `GET /plans/{plan_code}` | public | `?active=true\|false` |
| `GET /members` | any role | filters `member_id`, `last_name`/`first_name` (case-insensitive prefix), `date_of_birth`, `status`, `plan_code`, `state`; `page` (≥1), `page_size` (1–100, default 20), `sort` = `last_name`\|`member_id`\|`date_of_birth` → `{items, page, page_size, total, total_pages}` |
| `GET /members/export.csv` | any role | same filters; `text/csv` attachment `members.csv` (max 1000 rows, no SSN) |
| `GET /members/{id}`, `GET /members/{id}/claims` | any role | `404` for an unknown id, `422` for a malformed one |
| `PUT /members/{id}` | ADMIN, EXAMINER | send every field plus the current `version`. A stale version is `409`; an inactive plan is `422` |
| `GET /claims`, `GET /claims/{id}` | any role | filters `member_id`, `status`; paging as for members |
| `POST /claims` | ADMIN, EXAMINER | `201` + `Location`. A duplicate `external_ref` is `409` (+ `existing_claim_id`); a validation or business-rule failure (inactive member, future `service_date`, amount with more than 2 decimals) is `422` |
| `POST /admin/reset` | ADMIN | restores the seed → `{"plans":6,"members":250,"claims":377}` |

Details:
- **Every operation** accepts `?delay_ms=0..30000` to simulate a slow backend (for wait and timeout tests), and echoes `X-Request-ID` (it generates one if the request has none).
- Errors are RFC 9457 `application/problem+json`: `{type, title, status, detail, errors[{field, message, type}]}`. A missing, invalid or expired token is `401` with `WWW-Authenticate: Bearer`; the wrong role is `403`.
- Tokens are HMAC-signed and last `NWH_SANDBOX_TOKEN_TTL_SECONDS` (default 3600). Lower it to test expiry.
- Money is a JSON number with at most 2 decimals. `ssn` is returned on member detail, so mask it in evidence (`Sensitive`).

### Sign-in accounts (synthetic)
| Username / client | Password / secret | Role |
|---|---|---|
| `admin` | `pw-Northwind-admin` | ADMIN |
| `examiner` | `pw-Northwind-examiner` | EXAMINER |
| `viewer` | `pw-Northwind-viewer` | VIEWER (read-only) |
| `locked` | `pw-Northwind-locked` | locked account (`423`) |
| `nwh-batch` (client) | `cs-Northwind-batch` | EXAMINER |
| `nwh-reporter` (client) | `cs-Northwind-reporter` | VIEWER |

## Web app (`web/`)
A Vite + Preact + TypeScript single-page app served by nginx at `http://127.0.0.1:18081`. nginx proxies `/api/` to the API, so pages and the API share one origin. `GET /healthz` is the liveness check. Use the sign-in accounts above. Sessions are per tab (`sessionStorage`), so each browser context signs in on its own.

| Page | What it exercises |
|---|---|
| `/login` | labelled Username/Password, `Sign in` button; errors `data-testid="login-error"` (wrong password, locked account); `?next=` deep-link return; an expired or invalid token redirects here with "Your session has expired…" (`login-notice`) |
| `/members` | `role=search` form: Member ID (format check), Last name, First name, Date of birth (`type=date`), **Status** and **Plan** `<select>`s, `Search`/`Clear`. Results `data-testid="member-results"` table (rows `member-row` with `data-member-id`), `result-summary`, `Rows per page` select, `Previous page`/`Next page` + `page-indicator`, empty state `no-results`, `Export CSV` (download `members.csv`). The criteria live in the URL (back/forward, deep links) |
| `/members/{id}` | name/id/status badge; **tabs** (`role=tablist`, arrow keys): Overview (`dl`, masked SSN with `Show SSN` toggle), `Claims (n)` (`claims-table`), Plan (`Open plan brochure` → **new tab**). ADMIN/EXAMINER: `Edit member`, `Deactivate member` → **modal `<dialog>`** (`Deactivate`/`Cancel`) → toast `Member deactivated.` |
| `/members/{id}/edit` | form with labels, client validation (`aria-invalid`, `aria-describedby`, error summary `error-summary`), server `422` mapped to fields, `409` conflict with `Reload`, `Save changes` → toast `Member updated.`; VIEWER sees "You don't have permission…" |
| `/plans/{code}` | public brochure page (the new-tab target) |

- `?delay_ms=N` on any page URL slows every API call for the rest of the tab session. Use it for loading states and auto-wait tests; `?delay_ms=0` turns it off. A loading indicator is `data-testid="loading"` with `role=status`.
- Dates render as ISO `yyyy-mm-dd`; money renders as `$1,234.56`.
- Local development without Docker: `npm install`, then `npm run dev` in `web/` (proxies `/api` to the API port 18083).
