# ADR-0011 Own reporting engine instead of Allure/JUnit
Status: Accepted
Context: Reporting is a product differentiator: historical trends, flaky analytics, failure-signature grouping, traceability, white-labeling, and BI integration. Allure adds a Java dependency and its data model limits these; JUnit XML is lossy.
Decision: Canonical versioned result model (events + aggregates, JSON Schema) → own single-file HTML report (TypeScript) → SQL history store with documented star schema and views → sinks for ADO (REST Test Runs), Jira (Xray/Zephyr REST), Power BI (direct SQL, files, or push).
Consequences: We own UI and schema evolution. ADO "Tests" tab is fed via REST instead of `PublishTestResults@2`. If a customer's tool requires JUnit/xUnit files, that is an optional **exporter plugin**, never a core dependency.
