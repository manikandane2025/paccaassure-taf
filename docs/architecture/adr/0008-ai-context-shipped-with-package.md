# ADR-0008 AI context ships inside the package
Status: Accepted
Context: Variant-suite agents must know the exact core + product API of the *pinned* versions, with no access to other repos.
Decision: paccaassure-taf-core and every app pack wheel include `_ai/` (CONTEXT.md, generated catalogs, recipes, golden examples). `pataf ai sync` copies them to `.pataf/context/<package>@<version>/` in the consumer repo and regenerates the consumer `CLAUDE.md` import block. CI fails if synced context is stale vs. the lockfile.
Consequences: Context is always version-correct; upgrading a package upgrades its context.
