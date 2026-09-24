Add a typed API endpoint: $ARGUMENTS

1. Read `docs/specs/DRIVERS.md` (API) and search `docs/catalog/surfaces.md` for the service client.
2. Define request/response pydantic models (mark PHI fields `Sensitive[...]`), then `Endpoint[Req, Resp]`, then a method on the `<Service>Api` client.
3. If an OpenAPI spec is configured, verify models against it.
4. Add positive + one negative scenario (`call_raw`, status and error body).
5. Run mypy, ruff, pataf lint, pataf catalog.
