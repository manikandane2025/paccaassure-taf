# Product principles

PaccaAssureTAF is sold to multiple enterprise customers. Every design choice is judged by: *can a new customer adopt this in weeks, without us changing core code?*

## 1. Customer neutrality
- Core contains no customer knowledge. Customer specifics live in the customer's **app packs** and **variant suites**, which are their repos and their IP.
- Terminology maps per customer. The glossary gives neutral terms, and a customer's onboarding doc maps their words to ours (e.g. "product" → app pack, "state program" → variant).
- The demo company **Northwind Health** is used in the sandbox, examples, docs, and sales demos.

## 2. Packaging and distribution
- `paccaassure-taf-core` is a Python wheel. The base install covers web (Playwright), API (httpx), BDD, results, report and SQLite history. Optional extras:

  | Extra | Adds | For |
  |---|---|---|
  | `[desktop]` | Appium-Python-Client | Windows desktop |
  | `[jsp]` | (reserved; no extra deps today — JSP builds on web + httpx) | legacy JSP |
  | `[db-oracle]` `[db-mssql]` `[db-mysql]` `[db-postgres]` | python-oracledb · pyodbc · PyMySQL · pg8000 | app DB checks |
  | `[history-postgres]` `[history-mssql]` | pg8000 · pyodbc | shared history store |
  | `[secrets-azure]` `[secrets-hcv]` | azure-identity + azure-keyvault-secrets · hvac | secret providers |
  | `[api-contract]` | openapi-core | OpenAPI contract checks |
  | `[files]` | openpyxl, pypdf | Excel / PDF readers |
  | `[export-parquet]` | pyarrow | `pataf history export --format parquet` |
  | `[sinks-ado]` `[sinks-jira]` `[sinks-powerbi]` `[sinks-teams]` `[evidence-blob]` | httpx-based clients; msal / azure-storage-blob where needed | result & evidence sinks |

  Every extra's dependencies pass the license allow-list (ADR-0010). Exact pins live in `pyproject.toml`.
- Delivery: a private package index per customer (e.g. Azure Artifacts, JFrog, Nexus) plus a runner container image.
- `paccaassure-taf-report-ui` is built in this repo and embedded in the wheel as a static template. Customers never need Node.
- Release train: minor versions monthly, patches as needed, and an LTS line every 12 months with 18 months of support. A support matrix covers Python, OS, browsers, Appium drivers, DBs, ADO Server/Services, and Jira DC/Cloud.

## 3. Licensing and entitlements (ADR-0010)
- An offline-verifiable signed license file (Ed25519) includes customer, expiry, seats or agents, and entitled features (e.g. `desktop`, `history`, `sinks.powerbi`).
- Checks happen **only at CLI entry points** (run start, report build, sink publish). They never happen mid-scenario, and they never phone home.
- When a license expires: tests still run, but a banner appears in reports and entitled extras degrade gracefully. We never break a customer's release pipeline without warning.
- Third-party license compliance: an SPDX-aware allow-list check (`scripts/check_licenses.py`, policy in `scripts/license_policy.toml`) for Python and `license-checker` (npm, from Phase 3) run in CI. An SBOM (CycloneDX) is produced per release.

## 4. White-label and branding
- The report theme is configurable per customer: logo, product name, colors, and footer. It is set in config and embedded at build time.
- Customer-facing text (CLI messages, report labels) goes through a message catalog, so it is i18n-ready. English ships first.

## 5. Trust and security posture (sold into regulated industries)
- No telemetry by default. Optional anonymous usage telemetry is opt-in and documented.
- Everything can run on-prem or air-gapped. There are no runtime CDN calls, and the report works offline from a file.
- Masking is on by default. Evidence retention is configurable. Security docs cover a threat model, a data-flow diagram, and hardening.
- Signed releases and container images. Vulnerability scanning (pip-audit, npm audit, Trivy) runs in CI.

## 6. Onboarding a new customer (target: under 2 weeks to first green pipeline)
1. Install and run `pataf doctor`.
2. Scaffold app packs and variant suites with `copier` templates.
3. Configure environments, secrets, TMS, the history store, and sinks.
4. Migrate or author the first smoke suite (AI-assisted recipes).
5. Import the pipeline templates.
6. Connect Power BI to the history store views.

## 7. Roadmap hooks (design for, don't build yet)
- **PaccaAssureTAF Hub**: an optional self-hosted server (FastAPI) that serves the same report UI in live mode over the shared history store, with a multi-project portfolio view and SSO.
- A test data service connector, visual regression, mobile (Appium iOS/Android), and performance smoke.
