Migrate legacy Selenium/Java/TestNG script(s): $ARGUMENTS

1. Classify each script: Reuse / Refactor / Rebuild / Retire / Blocked — write the classification + reason in the PR description first.
2. Map Java POM → PaccaAssureTAF surface: `@FindBy`/`By.*` → typed element with PaccaAssureTAF `By`; `WebDriverWait`/`Thread.sleep` → remove (auto-wait) or `expect`; TestNG `@DataProvider` → pydantic data profiles or Scenario Outline with typed tables; assertions → `expect`.
3. Search the catalog; reuse existing pages/steps from the app pack rather than recreating.
4. Put app-generic parts in the app pack, variant-specific parts in the variant suite.
5. Keep the TMS/RTM ID as `@tms:` tag; note any lost coverage explicitly.
6. Dry-run, run, lint, catalog. Report: migrated, reused components, new components, gaps.
