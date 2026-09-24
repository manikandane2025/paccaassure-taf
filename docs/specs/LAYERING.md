# App packs and variant suites

Neutral terms, mapped per customer during onboarding (e.g. one customer's "product" = app pack, "state program" = variant).

## What lives where
| Concern | Core | App pack | Variant suite |
|---|---|---|---|
| Element types, drivers, runner, reporting, history, sinks | ✅ | — | — |
| Pages/screens/endpoints of the application | — | ✅ | override only |
| App flows & reusable steps | — | ✅ | extend/override |
| App smoke/regression features | — | ✅ | — |
| Variant-specific rules and workflows | — | — | ✅ |
| Variant regression packs, release validation | — | — | ✅ |
| Env profiles, data profiles, evidence, sink config | defaults | app defaults | variant values |

## App pack shape (example: `northwind-claims`)
```
src/northwind_claims/
  CLAUDE.md          # app context: modules, roles, URLs, quirks
  pages/ screens/ endpoints/ flows/ steps/ data/models.py data/factories.py
  world.py           # ScenarioStore schema + World extensions
  plugin.py          # entry points: parse types, auth provider, step registration
  _ai/               # shipped context (generated)
features/
config/pataf.app.yaml
```
Steps register through the `paccaassure_taf.plugins` entry point, so variant suites get them by installing the pack.

## Variant suite shape (example: `northwind-state-ga`)
```
CLAUDE.md                     # generated context header + variant rules
pataf.variant.yaml          # variant id, app packs, envs, TMS, history store, sinks, tags
.pataf/context/             # synced core + app pack context (ADR-0008)
src/northwind_state_ga/
  overrides/  flows/  steps/  rules/
features/regression/  features/release/
data/profiles/*.yaml  envs/*.yaml
```

## Override mechanism (type-safe)
```python
from northwind_claims.pages import MemberSearchPage

@overrides(MemberSearchPage)
class GaMemberSearchPage(MemberSearchPage):
    county = Dropdown[GaCounty](By.label("County"))

    def search(self, criteria: MemberSearchCriteria) -> "GaMemberSearchPage":
        if isinstance(criteria, GaMemberSearchCriteria) and criteria.county:
            self.county.select(criteria.county)
        return super().search(criteria)
```
- `@overrides` registers in the `SurfaceRegistry`; `w.page(MemberSearchPage)` and every `go(MemberSearchPage)` inside app-pack flows return the override for this variant.
- Overrides must subclass (checked at registration and by mypy). One override per surface per variant; conflicts fail at startup.
- Step rebinding requires `override=True`; `pataf lint` lists all rebinds.
- `pataf lint overrides` flags overrides whose base surface changed in a newer app pack version.

## Config resolution order
core defaults → `pataf.app.yaml` → `pataf.variant.yaml` → `envs/<env>.yaml` → `PATAF_*` env vars → CLI flags. `pataf config show --resolved` prints merged, masked config with each value's source.

## Result dimensions
Every result carries `project`, `app`, `variant`, `env` from config, so history, trends and Power BI can slice by any tier.
