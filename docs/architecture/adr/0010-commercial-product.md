# ADR-0010 Commercial, customer-agnostic product
Status: Accepted
Context: PaccaAssureTAF is sold to multiple customers; customers must adopt without core changes and must trust it in regulated environments.
Decision: (1) No customer knowledge in core; demo company Northwind Health for all examples. (2) Neutral terminology (app pack, variant suite) mapped per customer. (3) Offline signed license file (Ed25519) checked only at CLI entry points; graceful degradation on expiry. (4) Dependency license allow-list (MIT/BSD/Apache-2.0/PSF/MPL-2.0) enforced in CI; CycloneDX SBOM per release. (5) No telemetry by default; fully air-gap capable. (6) White-label report theming.
Consequences: Extra CI checks; license module in core; customer onboarding docs and templates are first-class deliverables.

Amendment 1 (2026-09-24, Accepted — Phase 0 review):
- The allow-list check understands SPDX expressions: `A OR B` passes if **any** option is allowed (e.g. python-oracledb `Apache-2.0 OR UPL-1.0`); `A AND B` passes only if **all** are allowed. Unknown/missing license metadata fails unless listed in `scripts/license_policy.toml` with a written justification.
- LGPL is not on the allow-list. PostgreSQL support in core (app DB and history store) uses **pg8000 (BSD-3-Clause)**; psycopg (LGPL) is never a core dependency, though customers may install it themselves and point SQLAlchemy at it.
- The check runs over the full dependency set (`uv sync --all-extras`) including dev tools, so nothing enters the lockfile unchecked. The sandbox's own dependencies are checked too, but separately (they never ship).

Amendment 2 (2026-09-24, Accepted — Phase 0 checkpoint 1):
- The allow-list adds **ISC** and **0BSD**: both OSI-approved, permissive, no copyleft, and functionally equivalent to MIT (0BSD even drops the attribution requirement). Trigger: `shellingham` (ISC), a required dependency of `typer`. Full list: MIT, MIT-0, BSD-2-Clause, BSD-3-Clause, 0BSD, ISC, Apache-2.0, PSF-2.0, Python-2.0, MPL-2.0.
- The temporary per-package exception for `shellingham` is removed; per-package exceptions remain for genuinely unusual cases only.

Open item (2026-09-25, owner: product owner — business decision, not engineering):
- The **tier split** — which capabilities are core vs licensed extras — is not final. `core.license.Entitlement` lists today's candidates (`desktop`, `jsp`, `history.shared`, `parallel`, `sinks.*`) so the mechanism is testable, but no feature is gated yet. In particular, **JSP may move to core**. Do not add entitlement checks to features until the split is decided.
