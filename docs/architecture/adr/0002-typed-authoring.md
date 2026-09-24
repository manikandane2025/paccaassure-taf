# ADR-0002 Typed authoring model
Status: Accepted
Context: Scripts must be easy for humans *and* agents to write correctly. Behave's `context` is an untyped bag and step args are strings.
Decision: (1) Typed element descriptors — only valid actions exist per element type. (2) Typed `World` injected into steps instead of raw `context`. (3) Step parameters typed from annotations with auto-registered parse types (enums, ids, dates, money). (4) Gherkin tables → `Table[Model]` validated by pydantic. (5) Navigation methods return the next page type. (6) mypy --strict everywhere.
Consequences: A thin `paccaassure_taf.bdd` layer over Behave is required; editors and agents get autocomplete and static errors instead of runtime failures.
