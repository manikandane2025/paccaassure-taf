# Drivers spec

All drivers sit behind `paccaassure_taf.elements` and are created lazily by `DriverFactory` plugins via the `World`. Sessions are configured only through typed config (`paccaassure_taf.core.config`).

## Web — `paccaassure_taf.web` (Playwright, sync)
- One `Browser` per worker; one `BrowserContext` per scenario (isolation); pages tracked per context.
- Config: browser (chromium/firefox/webkit/msedge), headless, viewport, base_url, locale, timezone, timeouts, `storage_state` per role (login once per worker, reuse per scenario).
- Features: auth state caching by `UserRole`, network interception helpers (`w.app.network.mock(...)`, wait-for-response), downloads/uploads, multi-tab, dialogs, accessibility snapshot check (axe via injected script, optional `@a11y` tag).
- Evidence: Playwright trace on failure (`retain-on-failure`), screenshot on failure + on `w.evidence.capture("name")`, optional video, HAR on `@har`.
- Remote: support `connect` to a Playwright server / cloud grid by config.

## JSP / Servlet — `paccaassure_taf.jsp`
Builds on `paccaassure_taf.web`, targeting legacy JSP/Servlet enterprise apps (framesets, full-page postbacks, Struts tokens).
- `JspPage.frame` default + `By.in_frame()` for framesets and nested iframes (framesets are resolved by name chain, e.g. `"top>content"`).
- `postback=True` on elements → click waits for navigation + `load`, then re-resolves frames.
- Session: detect session timeout pages and re-login transparently once (configurable), expose `JSESSIONID`.
- Popups: `with page.expect_popup(ChildWindowPage) as popup:` returns a typed page.
- Generated ids (`j_id0:form:j_id12`): lint forbids them; use `By.name`, `By.label`, or anchored xpath with `reason=`.
- `ServletClient`: an httpx client sharing cookies with the browser context; `submit_form(FormModel)` extracts hidden fields and tokens (Struts `org.apache.struts.taglib.html.TOKEN`, CSRF) from a GET before POST. Used for fast data setup and servlet-level checks.
- Encoding: default ISO-8859-1 fallback detection for old pages.
- IE mode: see ADR-0005 (not built unless required).

## API — `paccaassure_taf.api` (httpx)
- `ApiClient` per service, base URL from config, typed `Endpoint[Req, Resp]`.
- Auth providers (plugins): OAuth2 client credentials, Azure AD (MSAL), basic, API key, mTLS, cookie-from-browser.
- Retries with backoff for idempotent methods only; request/response logging with masking; timing captured.
- Contract checks: validate against OpenAPI spec (`openapi-core`) when `contract=` configured; JSON-schema snapshots.
- SOAP (legacy): optional `zeep` plugin if a product needs it.

## Desktop — `paccaassure_taf.desktop` (Appium 2)
- `DesktopSession` connects to a configured Appium server (local or remote Windows agent); `pataf doctor` checks server, driver, and developer mode.
- App launch modes: `app` path, attach to running window by title/handle, or `Root` session for multi-window flows.
- `DesktopScreen.window_title` → switch/wait for window; element model shared with web (`TextInput`, `Button`, `Grid[T]`, `Dropdown[E]`, `Tree`, `Menu`).
- Locator priority: AutomationId → AccessibilityId/Name → class + name → xpath (lint requires `reason=`).
- Evidence: window screenshot on failure, page source XML dump.
- Driver choice per ADR-0004 (spike: appium-windows-driver vs novawindows).

## DB — `paccaassure_taf.data.db`
- Named connections in config (e.g. `claims`, `eligibility`, `reporting`): Oracle (python-oracledb thin mode), MariaDB/MySQL (PyMySQL), SQL Server (pyodbc). Credentials via `SecretRef`.
- `Query[Row]` from `.sql` files with named binds only (no string formatting — lint rule). Read-only by default; write queries require `@db-write` tag and a `Mutation` type.
- Helpers: poll-until-row (`wait_for_row`), compare result sets with typed diffs.

## Files — `paccaassure_taf.data.files`
- Readers returning typed models: CSV, Excel (openpyxl), fixed-width (layout model), JSON, XML, PDF text (pypdf), and X12 EDI (834/835/837/270/271) via a pluggable parser.
- Comparators with tolerances and masked diffs; remote sources (SFTP, Azure Blob) via `DataProvider` plugins.
