# ADR-0012 History store and trend analytics
Status: Accepted
Decision: SQLAlchemy 2 + Alembic; backends SQLite (default local), PostgreSQL, SQL Server/Azure SQL. Star schema with stable views (`vw_*`) as the public BI contract; `history.json` rolling file for CI without a DB. Stable `test_key` with `@id` override. Analytics implemented in both SQL views and Python with contract tests for parity.
Consequences: Views are versioned like APIs; breaking view changes need a major version. Power BI and PaccaAssureTAF Hub read the same views.
