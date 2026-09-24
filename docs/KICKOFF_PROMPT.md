# First prompt to paste into Claude Code (from the repo root)

You are building PaccaAssureTAF (PaccaAssure Test Automation Framework), a commercial, customer-agnostic enterprise test automation product. The repository already contains its full context: CLAUDE.md, AGENTS.md, docs/PRODUCT.md, docs/architecture (ARCHITECTURE.md + ADRs 0001–0012), docs/specs (TYPED_AUTHORING, REPORTING, DRIVERS, LAYERING, INTEGRATIONS, CONFIG_SECRETS_DATA, AI_NATIVE), docs/conventions, docs/GLOSSARY.md, docs/BUILD_PLAN.md, and .claude/commands.

A reference framework is cloned at ../reference/GoldenTestAutomationFramework. It is inspiration only; we do not use Allure or JUnit and we contain no customer-specific content.

Do this now:
1. Read CLAUDE.md, PRODUCT.md, ARCHITECTURE.md, TYPED_AUTHORING.md, REPORTING.md and BUILD_PLAN.md fully. Skim the rest.
2. Summarize back in ≤ 15 bullets: the three tiers, the typed authoring model, the result → report → history → sinks pipeline, and the Phase 0 deliverables. List contradictions or gaps you find.
3. Execute Phase 0 step 1 only: study the reference repo and fill docs/REFERENCE_FRAMEWORK_NOTES.md.
4. Stop and wait for my review before scaffolding code.

Standing rules: follow BUILD_PLAN phase gates; update docs in the same change when a design shifts; no sleeps, no untyped public APIs, no real or customer data, no GPL/AGPL dependencies; ask when a decision isn't covered by an ADR.
