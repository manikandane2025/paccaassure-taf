# paccaassure_taf.elements

Driver-neutral typed element descriptors and the `By` locator vocabulary.

**Status:** empty skeleton (Phase 0). Built in **Phase 2** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `By` (role, label, test_id, text, css, xpath, name, automation_id, accessibility_id)
- `Button`, `TextInput`, `SecretInput`, `Dropdown[E]`, `Table[T]`, `Grid[T]`, `Dialog`, …
- `expect`

## Layer
- May import: evidence, results, core.
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Each element type exposes only valid actions (a `TextInput` has no `.click()`).
- Elements are class attributes on surfaces, so catalogs can list them.
- Every action emits a sub-action event; no free-text log messages.
- No driver imports here: adapters in web/jsp/desktop translate `By`.

## How to extend
- New element type: subclass the element base, register an `ElementType` plugin, add adapter readers.

## Read first
TYPED_AUTHORING.md §1–2, §7 · root `CLAUDE.md` hard rules.
