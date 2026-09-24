# ADR-0002 Typed authoring model
Status: Accepted
Context: Scripts must be easy for humans *and* agents to write correctly. Behave's `context` is an untyped bag and step args are strings.
Decision: (1) Typed element descriptors — only valid actions exist per element type. (2) Typed `World` injected into steps instead of raw `context`. (3) Step parameters typed from annotations with auto-registered parse types (enums, ids, dates, money). (4) Gherkin tables → `Table[Model]` validated by pydantic. (5) Navigation methods return the next page type. (6) mypy --strict everywhere.
Consequences: A thin `paccaassure_taf.bdd` layer over Behave is required; editors and agents get autocomplete and static errors instead of runtime failures.

Amendment 1 (2026-09-24, Accepted — Phase 0 review):
- (2) is refined: `World` is **generic over the scenario store**, `World[S]`. Each app pack declares its store as a dataclass and exports an alias (`ClaimsWorld = World[ClaimsScenario]`); steps annotate that alias, so `w.scenario` is fully typed. Plain `World` (no parameter) remains valid for steps that don't touch scenario state.
- (3) is refined: step patterns use bare `{name}` placeholders; the parse type is taken from the parameter annotation only (one source of truth).
- Gherkin tables reference scenario data with `${path}` (not `<path>`, which collides with Scenario Outline substitution).
- Open, to finalize in Phase 2 (Amendment 2): how a variant suite composes stores from several app packs (candidates: dataclass multiple inheritance of pack stores vs. a keyed per-pack sub-store `w.scenario[ClaimsScenario]`). Choose the option that keeps mypy strict and is simplest for scripters.
