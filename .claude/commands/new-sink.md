Add a result sink (integration): $ARGUMENTS

1. Read `docs/specs/REPORTING.md` §1 and §5, ADR-0007 and ADR-0011.
2. Implement `ResultSink` in `src/paccaassure_taf/sinks/<name>/` consuming only `RunResult` (+ history API if needed). Never import drivers or bdd.
3. Typed config model for the sink (endpoints, auth via SecretRef, mapping options); register under entry-point group `paccaassure_taf.sinks`; add an install extra.
4. Idempotency key per run; retries with backoff; `SinkReport` of what was created/updated; masked payload logging.
5. Tests: unit tests with recorded HTTP fixtures (respx), contract test of payload mapping from a fixture `run.json`.
6. Docs: sink section in REPORTING.md, config reference, CHANGELOG; regen catalog.
