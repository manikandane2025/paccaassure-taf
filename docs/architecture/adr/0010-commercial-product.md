# ADR-0010 Commercial, customer-agnostic product
Status: Accepted
Context: PaccaAssureTAF is sold to multiple customers; customers must adopt without core changes and must trust it in regulated environments.
Decision: (1) No customer knowledge in core; demo company Northwind Health for all examples. (2) Neutral terminology (app pack, variant suite) mapped per customer. (3) Offline signed license file (Ed25519) checked only at CLI entry points; graceful degradation on expiry. (4) Dependency license allow-list (MIT/BSD/Apache-2.0/PSF/MPL-2.0) enforced in CI; CycloneDX SBOM per release. (5) No telemetry by default; fully air-gap capable. (6) White-label report theming.
Consequences: Extra CI checks; license module in core; customer onboarding docs and templates are first-class deliverables.
