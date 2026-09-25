# paccaassure_taf.jsp

Legacy JSP/Servlet web on top of `web`: framesets, postbacks, session recovery, popups, `ServletClient`.

**Status:** empty skeleton (Phase 0). Built in **Phase 6** — see `docs/BUILD_PLAN.md`.

## Planned public API
- `JspPage` (default `frame`)
- `postback=True` elements
- `ServletClient.submit_form(FormModel)`

## Layer
- May import: web, elements, data, evidence, results, core.
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Frames resolved by name chain (`top>content`).
- Generated ids (`j_id…`) are forbidden by lint.
- Struts/CSRF tokens extracted from GET before POST.

## How to extend
- New legacy quirk: add a typed option on `JspPage`/element, plus a sandbox JSP page exercising it.

## Read first
DRIVERS.md (JSP), ADR-0005 · root `CLAUDE.md` hard rules.
