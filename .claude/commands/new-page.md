Create a typed page/surface: $ARGUMENTS

1. Read `docs/specs/TYPED_AUTHORING.md` §1–4 and the nested `CLAUDE.md` of the target package.
2. Search `docs/catalog/surfaces.md` — if a page for this screen exists, extend it instead (or create a variant override per `docs/specs/LAYERING.md`).
3. Choose base: `WebPage` (modern web), `JspPage` (legacy JSP), `DesktopScreen` (Windows), `Endpoint` (API).
4. Declare elements as typed class attributes. Locator priority: role/label/test_id → name → css → xpath with `reason=`.
5. Add intent-level methods (one surface each); navigation returns the next page type; docstring with example.
6. Add or update a sandbox/example scenario that uses it.
7. Run: `uv run mypy src && uv run ruff check . && uv run pataf lint && uv run pataf catalog`. Fix everything before finishing.
