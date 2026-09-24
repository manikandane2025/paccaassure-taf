# AI-native design

"AI-native" here means: **the repository is its own complete prompt.** Any coding agent opening any PaccaAssureTAF repo (core, app pack, or variant suite) can script or extend correctly without outside explanation.

## 1. Context hierarchy (progressive disclosure)
| File | Scope | Size budget |
|---|---|---|
| `/CLAUDE.md` | mission, hard rules, commands, map of docs | < 150 lines |
| `src/paccaassure_taf/<pkg>/CLAUDE.md` | package purpose, public API, invariants, extension recipe | < 60 lines each |
| `docs/specs/*` | deep specs, read on demand | no limit |
| `docs/catalog/*` (generated) | every step, page, element, flow, endpoint, data model, parse type | generated |
| `.claude/commands/*` | task recipes as slash commands | < 80 lines each |
| `examples/` + `docs/ai/golden/` | canonical, compiling examples to copy | real code |
Agents read root → the nested file for the area they touch → specs/catalog only as needed.

## 2. Generated catalogs (`pataf catalog`)
Introspects registries and docstrings; writes Markdown + JSON:
- `steps.md`: pattern, typed params, owning package, example usage, source path.
- `surfaces.md`: pages/screens/endpoints with elements (name, type, locator) and methods (signature + first docstring line).
- `flows.md`, `data-models.md`, `parse-types.md`, `tags.md`, `config-reference.md`, `sinks.md` (installed sinks + config), `result-schema.md` (fields of the result model), `history-views.md` (BI contract).
CI fails if the catalog is stale (`pataf catalog --check`). Agents must search the catalog before creating new steps or pages (rule 6).

## 3. Context shipped with packages (ADR-0008)
- Build step copies `docs/catalog`, package `CLAUDE.md` files, `TYPED_AUTHORING.md`, and golden examples into `paccaassure_taf/_ai/` inside the wheel.
- In app packs and variant suites, `pataf ai sync` writes `.pataf/context/paccaassure-taf-core@1.4.2/…` and `.pataf/context/northwind-claims@2.0.1/…` and regenerates the consumer `CLAUDE.md` block:
  ```
  <!-- pataf:context:begin (generated — do not edit) -->
  Read .pataf/context/paccaassure-taf-core@1.4.2/CONTEXT.md and .pataf/context/northwind-claims@2.0.1/CONTEXT.md
  <!-- pataf:context:end -->
  ```
- Result: an agent in a variant suite sees exactly the API of the versions it has installed.

## 4. Guardrails that make agent output correct
- mypy --strict, ruff, import-linter, and `pataf lint` (steps, tags, locators, overrides) run in pre-commit and a Claude Code PostToolUse hook.
- `pataf run --dry-run` proves every Gherkin step resolves.
- `pataf lint steps` detects duplicate/near-duplicate patterns (normalized text + parameter shape) to stop agents from inventing synonyms.
- Locator lint: flags generated ids, absolute xpaths, nth-child chains, text locators on dynamic data.

## 5. Agent workflows (slash commands in `.claude/commands/`)
`/new-page`, `/new-steps`, `/new-endpoint`, `/new-desktop-screen`, `/migrate-selenium-java`, `/triage-failure` (uses results + history), `/new-sink`, `/change-result-schema`, `/new-framework-feature`. Each recipe: read X → search catalog → generate → run checks → update catalog.

## 6. Authoring aids (optional, later phases)
- Playwright MCP / Playwright codegen to discover locators on a live page, then convert to typed page classes (`pataf gen page --from-url`).
- `pataf triage --run <id>` bundles failure signatures, history for each signature, and masked evidence for an agent to classify (product bug / script / env / data).
- Migration assistant: Selenium Java POM → PaccaAssureTAF page class mapping table (see `/migrate-selenium-java`).
