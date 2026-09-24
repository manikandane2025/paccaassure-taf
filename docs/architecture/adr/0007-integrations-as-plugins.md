# ADR-0007 Integrations are plugins
Status: Accepted (amended by ADR-0011)
Decision: ADO, Jira (Xray, Zephyr Scale), Power BI, Teams, webhooks implement `ResultSink` / `Notifier` in `paccaassure_taf.sinks.*`, installed via extras and enabled by config. They consume only `RunResult` (and history), never drivers. Linking uses `@tms:`, `@req:`, `@id:` tags. Publishing is idempotent and runs after the suite.
