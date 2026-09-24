# Reference framework harvest notes

Reference repo: `manikandane2025/GoldenTestAutomationFramework` (clone locally to `../reference/GoldenTestAutomationFramework`; it is **read-only inspiration**, never copied wholesale).

## Task for the agent (Phase 0)
1. Read the reference repo's README, structure, config, base classes, steps, hooks, reporting, and CI files.
2. Fill the table below: one row per notable capability.
3. Mark each: **Keep idea** (re-implement in PaccaAssureTAF style), **Adapt** (keep concept, change design), **Drop** (reason).
4. List gaps the reference does not cover that PaccaAssureTAF requires (at minimum: desktop/Appium, JSP specifics, typed World/steps, override registry, shipped AI context, own result model + HTML report + history/trends (replacing any Allure/JUnit usage), ADO/Jira/Power BI sinks, sensitive-data masking, sharding, licensing, customer neutrality).
5. Commit this file before writing any framework code.

| Capability | Where in reference | Decision | Notes for PaccaAssureTAF |
|---|---|---|---|
| _to fill_ | | | |

## Rules
- Do not copy code verbatim; rewrite to PaccaAssureTAF typing and layering rules.
- If the reference has a better idea than a spec here, propose an ADR instead of silently diverging.
