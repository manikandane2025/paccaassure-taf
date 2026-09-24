# ADR-0001 Core stack: Python + Behave + Playwright
Status: Accepted
Context: Target enterprise customers standardize on BDD with business-readable features; many are migrating from Selenium/Java/TestNG estates.
Decision: Python 3.12+, Behave runner, Playwright **sync** API (Behave is synchronous), uv for packaging/workspaces.
Consequences: Java scripts are converted (AI-assisted recipes), not wrapped. Behave lacks native parallelism, typing and reporting — solved by ADR-0006, ADR-0002 and ADR-0011.
