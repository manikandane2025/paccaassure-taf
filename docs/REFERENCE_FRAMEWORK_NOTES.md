# Reference framework harvest notes

Reference repo: `manikandane2025/GoldenTestAutomationFramework`, cloned to `../reference/GoldenTestAutomationFramework` at commit `9d328ea` (16 commits, 2026-01-15 → 2026-09-01). It is **read-only inspiration**. We never copy it wholesale.

## Rules
- Do not copy code verbatim. Rewrite everything to PaccaAssureTAF typing and layering rules.
- If the reference has a better idea than one of our specs, propose an ADR or spec edit (§6). Do not diverge silently.
- These notes deliberately leave out reference data values and project identifiers that look customer-specific (hard rule 1).

---

## 1. Reference overview

| Aspect | Reference |
|---|---|
| Language | Python 3.11 (`Dockerfile` base `python:3.11-slim`; `cpython-311` `.pyc` files in the initial commit `d66d1bf`) |
| Runner | Behave, driven in-process by `runner.py` through `behave.__main__.main` |
| UI | Playwright **async** API (`playwright.async_api`) with async Behave steps |
| API / DB | `requests`, `jsonschema`, SQLAlchemy (plus `pymongo`, which is imported but not declared) |
| Reporting | A custom Behave JSON formatter feeds a Jinja2 HTML template, and the result is written into a per-run zip |
| Config | PyYAML files per env + `constants.py` + `test_runner_instance.json` |
| Dependencies | `requirements.txt` is **UTF-16 encoded** and mostly unpinned (only Jinja2, MarkupSafe and requests-toolbelt are pinned). `six` and `pymongo` are used but missing. No pyproject, no lockfile. |
| Quality tooling | None: no tests, no linters, no type checking, no pre-commit, no CI pipeline files (`AIContext/07_CICD_and_Runners.md` describes CI only in prose), no README |
| Size | 66 files, about 5.5k lines of Python, 15 AIContext markdown docs |

```
GoldenTestAutomationFramework/
├── runner.py  constants.py  test_runner_instance.json  requirements.txt  Dockerfile
├── config/        AUT_Configurations.yaml  Framework_Config.yaml  browser_settings.yaml  {dev,qa,int}_config.yaml
├── clients/       PlayWrightClient.py  WebElements.py  api_client.py  db_client.py  SQLite3_client.py  JsonClient.py  YAMLClient.py
├── pages/         BasePage.py  GoogleSearchPage.py  swagapi.py
├── features/      *.feature (emptied at HEAD)  environment.py  steps/*.py
├── CustomJsonReportFormatter/custom_json_formatter.py
├── Utility/       frameworkDataContext.py  HTMLReportGenerator.py
├── templates/     report_template_v2.html (+4 other HTML templates)
├── performance/   k6 smoke + report     security/ ZAP baseline     runbooks/     scripts/ image build
├── AIContext/     01–15 *.md (framework rules + "Automation Architect" agent workflow)
└── logs/ reports/ (run artifacts committed to Git)
```

**How a test flows from feature file to browser**
1. `python runner.py --env dev`. **Importing** `runner.py` already configures logging, writes `test_runner_instance.json` (a new run id and absolute paths) to the cwd, creates a SQLite DB, and loads env YAML (`runner.py:65,103,128,212,285`).
2. `create_artifacts_zip()` creates `reports/Test_Results_Artifacts_<ts>.zip`. `run_behave_tests()` walks `features/`, builds the args (default tag `@playwrighttests` plus CLI tags), and, if parallel, splits the feature list round-robin across a `multiprocessing.Pool` (`runner.py:466-472`).
3. Each worker calls `behave_main(args + --format=CustomJSONFormatter --outfile=behave_report_<ts>.json)`.
4. `features/environment.py:before_all` starts an async Playwright instance that nothing uses. A Given step then calls `PlaywrightClient.create(application_url=...)`, which reads `config/browser_settings.yaml` relative to the cwd, launches browser, context and page, and navigates (`clients/PlayWrightClient.py:41-45,105-260`).
5. The step builds a page object (`pages/*.py`). Its `__init__` constructs `WebElements` wrappers from selector strings. Actions log, and on error take a screenshot into the `CustomContext` singleton (`clients/WebElements.py:47-70`) and re-raise as `AssertionError`.
6. `after_step` takes another screenshot on failure. The formatter's `result()` gathers `inputdata*`, `outputdata*` and `screenshot*` keys from `CustomContext` into the step JSON (`custom_json_formatter.py:157-214`). `after_scenario` closes every client it finds by scanning `context` attributes for class names.
7. The runner merges the per-worker JSON, computes counts, writes `Consolidated_Test_report_<ts>.json`, renders `report_template_v2.html` with Jinja2, and writes the HTML **only into the zip** (`runner.py:616-649`).

---

## 2. Harvest table

Decision key: **Keep idea** = re-implement the concept in PaccaAssureTAF style. **Adapt** = keep the concept but change the design. **Drop** = conflicts with our specs or is obsolete.

| Capability | Where in reference (paths) | Decision | Rationale | How it maps to PaccaAssureTAF (module/spec) | Build phase |
|---|---|---|---|---|---|
| Single CLI entry point | `runner.py` | Adapt | A single entry point is good. But import-time side effects, argparse bugs (§4) and untyped globals make it unreliable. | `paccaassure_taf.runner` (Typer) `pataf run` · ARCHITECTURE §4 | 2 |
| Env selection + per-env YAML | `config/{dev,qa,int}_config.yaml`, `runner.py:244-285` | Adapt | Env overlays are right. Here they are three near-identical full copies, untyped, silently default to `dev`, and are loaded but never consumed. | `core.config` (pydantic-settings), `envs/<env>.yaml` overlays, `pataf config show --resolved` · CONFIG_SECRETS_DATA, LAYERING | 1 |
| Global constants module | `constants.py` | Drop | Config is split across constants and YAML, paths are relative to the module, and it holds a customer-looking project code. | Typed `PatafConfig` defaults | 1 |
| Vault paths instead of secret values | `config/*_config.yaml` (`*_vault_path` keys, commit `ee4b6ca`), `config/AUT_Configurations.yaml` | Keep idea | Config holds references, never values. `use_hashicorp_vault: "Yes"` strings should become typed. | `SecretRef` (`hcv://`, `kv://`, `env://`) + `SecretProvider` plugins · ADR-0009 | 1 |
| Browser settings + env overrides | `config/browser_settings.yaml`, `PlayWrightClient.py:105-245` | Adapt | Useful knobs: channel (chrome/msedge), headless, viewport, downloads, proxy, http credentials, geolocation, permissions, image blocking. The dict is loosely nested, several keys are ignored, and env vars are ad hoc (`PLAYWRIGHT_BROWSER`, `AA_ENFORCE_FIREFOX`). | `WebConfig` model; `PATAF_WEB__*` env overrides · DRIVERS Web | 2 |
| Browser lifecycle | `clients/PlayWrightClient.py` | Adapt | Here each step creates its own browser, context and page (one per client, several per scenario). | One Browser per worker, one BrowserContext per scenario, created lazily by `World` via `DriverFactory` · DRIVERS Web | 2 |
| Async Playwright + async steps | `features/environment.py`, `features/steps/*.py` | Drop | Sync hooks mix in `loop.run_until_complete` (`environment.py:65-73`). This is fragile, and ADR-0001 already chose the sync API. | — | — |
| Auth `storage_state` reuse | `PlayWrightClient.py:220-222,305-311` | Keep idea | Log in once and reuse. Here a single cwd file `auth_state.json` is shared by everything. | Per-`UserRole` storage state cached per worker · DRIVERS Web | 2 |
| Tracing | `PlayWrightClient.py:236-243,264-269` | Adapt | Here the trace is always on per session and written to `traces/`. | `retain-on-failure` trace stored as evidence · REPORTING §2 | 2 |
| Network block/mock | `PlayWrightClient.py:476-488` | Adapt | Useful helpers, but `route()` is never awaited, so they are silently ineffective. | `w.app.network.mock(...)`, wait-for-response · DRIVERS Web | 2 |
| Tabs and popups | `PlayWrightClient.py:436-460` | Adapt | These return raw `Page` objects. | `with page.expect_popup(ChildPage) as popup:` typed · DRIVERS JSP/Web | 2 / 6 |
| Visual comparison | `PlayWrightClient.py:462-474` | Drop | These call `to_have_screenshot`, which Playwright's Python `expect` does not provide (JS test-runner only), so they cannot work. | Roadmap: visual regression · PRODUCT §7 | — |
| Typed-ish element wrappers | `clients/WebElements.py` (TextBox, Button, Link, CheckBox, RadioButton, Dropdown, FileInput, Table) | Adapt | This is the right instinct: per-type actions, a human name in logs, failure capture per action. But elements are instance attributes built from a live `page`, so they cannot be catalogued. Every action takes a free-text `log_message`, every error becomes `AssertionError`, and queries swallow errors. | `paccaassure_taf.elements` typed descriptors, `.describe()`, sub-action events · TYPED_AUTHORING §2 | 2 |
| Selector vocabulary | `WebElements.SelectorType` (CSS/XPATH/ID/TEXT) | Adapt | CSS is the default. There are no role/label/test-id strategies, and the ID type is misused (§4). | `By.role/label/test_id/...` with lint priority · TYPED_AUTHORING §1 | 2 |
| Table helper | `WebElements.Table` | Adapt | Access is by row/column index, and selectors are built by interpolating text (`WebElements.py:502`). | `Table[T]` mapping headers to model fields, `row_where(...)` · TYPED_AUTHORING §2 | 2 |
| Frames | `WebElements.FrameElement` | Adapt | Frame proxies are built per element. | `By.in_frame()` + `JspPage.frame` name chain · DRIVERS JSP | 6 |
| Shadow-DOM component | `WebElements.WebComponent` | Drop | Playwright CSS pierces open shadow roots by default. Our `WebComponent` means a reusable page fragment, a different concept. | `paccaassure_taf.web.WebComponent` | 2 |
| Modals + native dialogs | `WebElements.Modal`, `WebElements.BrowserAlert` | Keep idea | Accept/dismiss/assert message for alert, confirm and prompt, and ESC-to-close. | `Dialog` element + typed dialog handling; JSP `alert()`/`confirm()` | 2 / 6 |
| File upload | `WebElements.FileInput` | Keep idea | Single and multiple uploads. | `FileUpload` element | 2 |
| Screenshot on failure | `WebElements._capture_on_failure`, `PlayWrightClient._client_capture_failure`, `environment.after_step` | Adapt | Right concept. But it is captured in 3 places, each after a fixed `sleep(0.5)`, stored base64 in a global singleton, and never masked. | Evidence captured once by hooks, masked, stored as file refs with sha256 · REPORTING §2, CONFIG_SECRETS_DATA | 2 |
| Page objects | `pages/BasePage.py`, `pages/GoogleSearchPage.py`, `pages/swagapi.py` | Adapt | POM is fine. Here elements live in `__init__`, pages hold assertions and hardcoded URLs, and methods return untyped `self`. | `WebPage` with class-attribute elements, `route: ClassVar`, typed `go()` · TYPED_AUTHORING §3 | 2 |
| Step definitions | `features/steps/*.py` | Adapt | Steps create drivers, hardcode credentials, and add suffixes to avoid phrase collisions. | Typed one-line steps over `World` · TYPED_AUTHORING §8 | 2 |
| Behave hooks | `features/environment.py` | Adapt | These close clients by scanning `context` for class-name strings. | `paccaassure_taf.bdd` hooks writing result events and managing sessions | 2 |
| Global data context | `Utility/frameworkDataContext.py` | Drop | An untyped process-global singleton with a key-prefix protocol that leaks state across scenarios. | Typed `World` + per-scenario `w.scenario` store · ADR-0002 | 2 |
| Step input/output data in report | `custom_json_formatter.py:157-214` (`Test_data`, `Test_Output_data`) | Adapt | Showing what data a step used or produced is valuable for testers. | `StepResult` typed params + proposed `outputs` (masked) · §6 P2 | 2 |
| Custom Behave formatter | `CustomJsonReportFormatter/custom_json_formatter.py` | Adapt | Shows that the formatter API can capture step timing and data. The shape is cucumber-like with no schema, naive local times, inline base64, and it writes only at feature end. | Event writer: `events-<worker>.jsonl` with `schema_version`, masked at write · REPORTING §1 | 2 |
| Merge of per-worker results | `runner.merge_json_reports` | Keep idea | Workers produce partial results that are then merged. | `results` merger → `run.json` · REPORTING §1 | 2 / 8 |
| Self-contained HTML report | `templates/report_template_v2.html`, `runner.render_html_report` | Adapt (concept) | Good: inline CSS/JS with no CDN, status donuts, status filter and search, feature → scenario → step drill-down, embedded screenshots. Weak: server-side Jinja, no history, and the file is written only inside the zip. | `reporting` + `report-ui` single-file TS template · REPORTING §3 | 3 |
| Other report templates | `templates/report_template.html`, `SupportingHTML.html`, `dynamic_table.html`, `nested_table.html` | Drop | Superseded or unused. | — | — |
| Field-mapping comparison report | `Utility/HTMLReportGenerator.py`, `templates/SubModuleReport_template.html` | Adapt | Useful: field-level source → target comparison with positional (start/length) fixed-width mapping and conditional mapping rules. But it runs at import and embeds data that looks like PHI (§4). | `data.files` fixed-width layouts + typed comparator + `report_panels` plugin · §6 P5 | 4 (+3) |
| Per-run artifact bundle | `runner.create_artifacts_zip`, `add_file_to_artifacts` | Adapt | Isolating artifacts per run id is good. Writing into a zip mid-run is not. | `results/<run-id>/` folder that CI zips · REPORTING §2–3 | 2 / 3 |
| Cross-process run state file | `runner.save_instance_to_file`, `test_runner_instance.json` | Drop | A cwd JSON file with retry-and-sleep IO is racy (§4). | Run id passed to workers via args/env; `run_id` on every event | 2 / 8 |
| Logging | `runner.configure_logging` | Adapt | File + console with run id. No masking, no structure, no test/step correlation. | structlog JSON with masking processors and run/test/step ids · INTEGRATIONS (Observability) | 1 |
| Feature-level parallelism | `runner.run_behave_tests` (Pool, `feature_dirs[i::n]`) | Adapt | The concept is ADR-0006 option (b). The implementation runs Behave in-process in Pool workers, the enable flag is broken, and it breaks on Windows spawn (§4). | Native sharder: a Behave subprocess per worker + `--shard i/N` · ADR-0006 | 8 |
| Scenario retry | `constants.SCENARIO_MAX_RETRIES`, `environment.retry_scenario` (no-op), formatter `retry_attempts` | Adapt | Declared but never implemented. | `@retryable` attempts, `flaky` status, history flaky score · INTEGRATIONS | 8 |
| Dry run | `runner.py --dry-run` | Keep idea | Validates that steps resolve without executing them. | `pataf run --dry-run` over typed steps | 2 |
| Tag filtering | `runner.construct_behave_args`, `constants.DEFAULT_TAGS` | Adapt | A default tag is always merged with OR semantics, and CLI tags are ignored (§4). | Tag expressions + `pataf lint tags` taxonomy · CODING_STANDARDS | 2 |
| REST client | `clients/api_client.py` | Adapt | Good checklist: basic, bearer, API key, JWT and HMAC-signature auth; honours 429 `Retry-After`; timing; jsonschema validation; pagination. Wrong design: `requests`, returns `None` on failure, retries non-idempotent verbs, sleeps, hardcoded refresh credentials, runs at import. | `ApiClient`, `Endpoint[Req, Resp]`, `AuthProvider` plugins on httpx · DRIVERS API | 4 |
| Response/query time checks | `api_client.validate_response_time`, `db_client.validate_query_time` | Keep idea | Timing as an explicit expectation. | Timing on sub-actions + `expect(...)` timing matcher | 4 |
| JSON/YAML dot-path utilities | `clients/JsonClient.py`, `clients/YAMLClient.py` | Drop | Untyped dict surgery contradicts "data is pydantic models". | Pydantic models; `data.files` readers | — |
| YAML `{{placeholder}}` templating | `YAMLClient.replace_placeholders` | Drop | Replaced by typed factories and data profiles. | `data` factories/profiles · CONFIG_SECRETS_DATA | — |
| SQL client | `clients/db_client.py` `SQLClient` | Adapt | Named binds are good. But `echo=True` logs SQL and params, `dict(row)` fails on SQLAlchemy 2, it retries with sleeps, and it writes freely. | `Query[Row]` from `.sql`, read-only default, `Mutation` + `@db-write` · DRIVERS DB | 4 |
| DB access broker before connect | `db_client.StrongDMClient` | Adapt (idea) | Checking or granting access through a broker before connecting is a real enterprise need. Here it is hard-wired and runs at import. | Proposed `ConnectionProvider` plugin type · §6 P7 | 4 |
| MongoDB client | `db_client.NoSQLClient` | Drop | Not in spec; `pymongo` undeclared. Could become a `DataProvider` plugin if a customer needs it. | — | — |
| SQLite "framework test-data DB" | `clients/SQLite3_client.py`, `runner.create_or_retrieve_framework_database` | Drop | f-string SQL, imports `runner` (side effects), unclear purpose. | Local data-reservation store (Phase 8) and SQLite history backend (Phase 5) are separate typed components | 5 / 8 |
| Container image | `Dockerfile`, `scripts/build_golden_image.{ps1,sh}` | Adapt | `playwright install --with-deps` is right. Wrong: Python 3.11, runs as root, pip without a lock, copies the whole repo including artifacts. | `docker/` runner image: uv + lock, non-root, pinned browsers · INTEGRATIONS | 8 |
| Performance smoke (k6) | `performance/*`, `runbooks/Perf_Security_Runbook.md` | Drop from core | k6 is **AGPL-3.0**, so it can never be a dependency or be bundled. Customers may run it themselves. | Proposed result importer plugin · §6 P6 | later |
| Security baseline (ZAP) | `security/zap_baseline.ps1` | Drop from core | Out of scope, and it uses the deprecated `owasp/zap2docker-stable` image. | Proposed result importer plugin · §6 P6 | later |
| Framework rules for agents | `AIContext/01–05, 07–09` | Adapt | Good content: layer boundaries, do's/don'ts, tagging, troubleshooting. But it is hand-written and has **drifted** from the code (§4). | CLAUDE.md hierarchy + generated catalogs + `--check` in CI · AI_NATIVE | 10 |
| Agent stage workflow / HITL | `AIContext/06, 10–15` | Adapt (selected ideas) | Keep: stage contracts, error-class → next-action loop, reviewer verdict schema, "never ask for secrets in chat". Out of scope: orchestration for a specific platform (demo UI, prompt DB, LLM profiles). | `.claude/commands` recipes, `/triage-failure` · §6 P8 | 10 |
| Tagging conventions | `AIContext/03_Tagging_Conventions.md` | Adapt | `@req`, `@owner` and suite tags align with ours. `@risk:<level>` is worth adopting. `@feature`, `@story` and `@e2e` overlap existing tags. | CODING_STANDARDS tag taxonomy · §6 P3 | 2 |
| Failure taxonomy | `AIContext/05, 06, 11_AA_Stage_Lifecycle.md` | Adapt | `SCRIPT_ERROR, LOCATOR_MISSING, TIMEOUT, ENV_DOWN, DATA_SETUP_FAILED, AUTH_FAILED, FLAKY`. `AUTH_FAILED` is missing from our categories. | `FailureInfo.category` + triage classes · §6 P1 | 2 |
| Run artifacts in Git | `logs/`, `reports/*.json`, `reports/*.zip`, `test_runner_instance.json` | Drop | Committed despite `.gitignore`. The initial commit also held `.pyc` files and a `.db`. | `.gitignore` for `results/`; CI artifacts only | 0 |
| Dependency manifest | `requirements.txt` | Drop | UTF-16, unpinned, incomplete. | `pyproject.toml` + `uv.lock` + license allow-list · ADR-0010 | 0 |

---

## 3. Strengths worth preserving
1. **Typed element wrappers** (`clients/WebElements.py`). The reference already models elements as classes with type-specific actions and human-readable names. This is the seed of our typed-element model.
2. **Wide widget coverage.** Frames, native dialogs, modals, file upload, tables, new tabs and popups, and downloads (`WebElements.py`, `PlayWrightClient.py`). Use it as a checklist for our element catalogue.
3. **Failure evidence by default.** Every failing action tries to capture a screenshot (`WebElements._capture_on_failure`).
4. **Step-level data in the report.** Inputs, outputs and screenshots per step (`custom_json_formatter.py:157-214`) make reports useful to manual testers and auditors.
5. **An owned, offline HTML report.** Inline CSS/JS with no CDN, donuts, filter and search (`templates/report_template_v2.html`). This supports ADR-0011's direction.
6. **References instead of secrets in config.** `*_vault_path` keys (commit `ee4b6ca`).
7. **Rich API auth coverage.** Basic, bearer, API key, JWT and HMAC signing, plus `Retry-After` handling (`clients/api_client.py`). A good test list for `AuthProvider` plugins.
8. **Useful Playwright knobs.** `storage_state` reuse, tracing, proxy, http credentials, geolocation, permissions, image blocking (`PlayWrightClient.py`).
9. **Written boundaries and a stable-contract mindset.** "Treat the JSON schema as a stable contract" (`AIContext/01_Framework_Overview.md`, Extension Points) matches our hard rule 8.
10. **An error taxonomy that drives next actions** (`AIContext/11_AA_Stage_Lifecycle.md`) and the HITL rule "never request secrets in chat; point to the vault" (`AIContext/13_*`).

## 4. Anti-patterns to avoid (with citations)
| Anti-pattern | Where | Our guard |
|---|---|---|
| Fixed sleeps | `asyncio.sleep(0.5)` before screenshots: `clients/WebElements.py:50,80,637`, `PlayWrightClient.py:90`. `time.sleep` in retries: `api_client.py:96,102,109,112,124`, `db_client.py:59,63,72,191,254,277`, `runner.py:94,120` | ruff banned-api `time.sleep`; `wait.until`; auto-wait |
| Untyped global state | `Utility/frameworkDataContext.py` singleton; key-prefix protocol `custom_json_formatter.py:163-177`; scanning `context` by class-name string `features/environment.py:18-36` | Typed `World`, `w.scenario` |
| Locators built at runtime / misused | Elements created in page `__init__` (`pages/*.py`). A CSS selector passed with `SelectorType.ID` becomes `#input[...]` (`pages/swagapi.py:23`). Index locator `>> nth=0` (`GoogleSearchPage.py:20`). Text locator on a full error sentence (`swagapi.py:25`). Text interpolated into a selector (`WebElements.py:502`) | Class-attribute descriptors, `By`, locator lint |
| Drivers created inside steps | `features/steps/swaplabs_steps.py:24-27`, `GoogleSearch_Steps.py:14` | Lazy sessions in `World` |
| Hardcoded URLs and credentials | URLs: `pages/swagapi.py:14,44`, `GoogleSearchPage.py:26`. Credentials: `swaplabs_steps.py:42,49`, `api_client.py:218,313-320`, `db_client.py:312,315` (password in a DSN) | Config `base_url`, `SecretRef`, gitleaks |
| Duplicate step phrases made unique with suffixes | `swaplabs_steps.py:59` ("… for swaplabs") vs `GoogleSearch_Steps.py:24` | `pataf lint steps` near-duplicate detection |
| Technology words in Gherkin | "a new Playwright client is initialized …" (`features/swaplabs.feature` at `8ae30df`) | Step vocabulary rules |
| Broken step state | `GoogleSearch_Steps.py:26` reads `context.googleclient`, which only the other feature sets | Typed `World` (mypy would flag it) |
| Assertions in pages, contradicting the reference's own rule | `pages/swagapi.py:42-52` vs `AIContext/01` ("No assertions in clients or pages") | §6 P4 |
| Every error becomes `AssertionError` | `WebElements.py:103-105,117,121,…` | Loses failed vs broken; our status semantics + `FailureInfo.category` |
| Swallowed errors / `None` returns | `WebElements.get_text` returns `""` (`:158-160`); `api_client._make_request/_validate_response` return `None` (`:119-131,188-194`); DB fetches return `[]` on error | Raise `PatafError` subclasses with actionable messages |
| **Side effects at import** | `runner.py:65,103,128,212,285`; `api_client.py:313-358` makes network calls on import and then raises `ValueError` (it unpacks 2-tuples into 4 names at `:291`), so the module **cannot be imported**; `db_client.py:312-332` also fails at import; `JsonClient.py:205-252`; `HTMLReportGenerator.py:91-102` writes a report on import; `SQLite3_client.py:5` imports `runner` | Import-time purity; ruff; unit tests import every module |
| Retrying non-idempotent calls | `api_client._make_request` retries POST/PUT/DELETE on 5xx and timeouts | Retries for idempotent methods only · DRIVERS API |
| Injection-prone SQL | `SQLite3_client.py:51-127` (table and condition strings) | Named binds only; `.sql` files; lint |
| Sensitive data in logs and artifacts | `TextBox.fill` logs the typed text, including passwords (`WebElements.py:260`); SQLAlchemy `echo=True` (`db_client.py:168`); unmasked base64 screenshots in JSON (`reports/*.json`, 228 KB for 2 scenarios) | `SecretInput`, `Sensitive[T]`, masking at event write |
| Data that looks like PHI committed | `Utility/HTMLReportGenerator.py:91` sample data contains SSN-shaped and government-program-ID-shaped values | Synthetic data only; gitleaks + PHI regex hook |
| Customer-looking identifiers in code | `constants.py:5` (project code) | Hard rule 1; Northwind Health |
| cwd-dependent paths and absolute paths in Git | `PlayWrightClient.py:19` default `config/browser_settings.yaml`; `runner.py:29,35`; committed `test_runner_instance.json` contains local absolute paths | pathlib, config-rooted paths |
| Timestamp mismatch that silently breaks durations | Formatter writes `%Y-%m-%d %H:%M:%S` (`custom_json_formatter.py:96`) but `runner.parse_time` only accepts ISO `T` formats (`runner.py:607`), so every scenario duration renders "N/A". All times are naive local. | UTC, typed datetimes, schema validation |
| CLI flags that do nothing | `--no-parallel` has `default='--no-parallel'`, so parallel is always off (`runner.py:674`); CLI `--tags` are parsed but `DEFAULT_TAGS` is passed (`:691`); comma-joined tags mean OR (`:292`) | Typer + typed options + CLI tests |
| Not safe on Windows spawn | Pool workers re-import `runner.py`, re-run the module side effects, and overwrite `test_runner_instance.json` with a new run id (`runner.py:27,103,470`) | Subprocess workers receive the run id explicitly |
| File encoding | `requirements.txt` is UTF-16. Files opened without `encoding=` (`runner.py:225`, `YAMLClient.py:23`, …) | ruff `PLW1514`; `.gitattributes`; UTF-8 everywhere |
| APIs Playwright Python does not have / missing awaits | `to_have_screenshot` (`PlayWrightClient.py:466,473`); `page.route` not awaited (`:478,483`) | mypy strict + sync API |
| Hook lifecycle bug | `after_scenario` stops the shared Playwright instance from `before_all` after **every** scenario (`environment.py:128-130`) | Session ownership in `World` |
| Docs drift from code | `AIContext/01` describes `security/`, `input/`, `output/`, `FrameworkTestDataDatabase/` factories and `Utility/` waits, none of which exist; requirements omit `six`/`pymongo` | Generated catalogs + `pataf catalog --check` |
| No runnable scenarios at HEAD | Feature files emptied in `35592a1`, `9d328ea` | Sandbox e2e scenarios kept green in CI |
| Artifacts and binaries in Git history | `logs/`, `reports/`, `.zip`; `.pyc` and `.db` in `d66d1bf` | `.gitignore`, `check-added-large-files` |
| AGPL tool shipped as a script | `performance/k6_smoke.js`, `run_k6.ps1` | License allow-list (ADR-0010) |
| Root container, no lock | `Dockerfile` | Non-root runner image, `uv sync --frozen` |

## 5. Gap list (what PaccaAssureTAF needs that the reference lacks)
| Required capability | Reference status | PaccaAssureTAF home | Phase |
|---|---|---|---|
| Windows desktop via Appium | Absent | `desktop` · ADR-0004 | 7 |
| JSP: framesets by name chain, postback waits, session-timeout recovery, generated-id handling, ISO-8859-1 | Only a generic `FrameElement` and popup helper | `jsp` · ADR-0005 | 6 |
| `ServletClient` (httpx sharing cookies; Struts/CSRF token extraction) | Absent | `jsp` | 6 |
| Typed `World` and typed steps with annotation-driven parse types | Absent (untyped `context` + global singleton) | `bdd` · ADR-0002 | 2 |
| `Table[T]` (Gherkin and UI tables → pydantic rows) | Absent (index-based `Table`) | `elements`, `bdd` | 2 |
| Auto-waiting typed `expect` with soft mode | Partial (raw Playwright `expect` in pages) | `elements` / `expect` | 2 |
| Flows layer | Absent | `flows` | 2 |
| Surface override registry for variant suites | Absent (single repo, no tiers) | `SurfaceRegistry`, `@overrides` · LAYERING | 10 |
| Plugin / entry-point system | Absent | `core` plugin registry · ARCHITECTURE §5 | 1 |
| Versioned result event model + JSON Schema | Absent (ad-hoc cucumber-like JSON) | `results` · ADR-0011 | 2 |
| Self-contained HTML report with evidence viewer, failures by signature, traceability | Partial (Jinja report without these) | `reporting` + `report-ui` | 3 |
| History store, trends, flaky score, baselines | Absent | `history` · ADR-0012 | 5 |
| Quality gates + exit-code contract | Absent (Behave exit code only) | `gates` | 5 |
| ADO Test Runs, Jira Xray/Zephyr, Power BI sinks | Absent | `sinks` · ADR-0007 | 9 |
| Sensitive-data masking (`Sensitive[T]`, masking at event write, screenshot blur) | Absent (actively logs secrets) | `core` masking, `evidence` · ADR-0009 | 1–2 |
| Parallel workers + CI sharding with merged run | Broken attempt | `runner` · ADR-0006 | 8 |
| Retries recorded as attempts, flaky status, quarantine | Declared, not implemented | `runner`, `results`, `gates` | 8 / 5 |
| Data profiles, factories, reservation, cleanup | Absent (docs describe a factory folder that does not exist) | `data` · CONFIG_SECRETS_DATA | 4 / 8 |
| Typed DB `Query[Row]` for Oracle / MySQL / SQL Server | Generic SQLAlchemy, untyped | `data.db` | 4 |
| File readers (CSV, Excel, fixed-width, X12, PDF) | Absent (only the report-side mapping comparison) | `data.files` | 4 |
| OpenAPI contract checks | Absent (jsonschema only) | `api` | 4 |
| Licensing (Ed25519 file, entry-point checks) | Absent | `core` license module · ADR-0010 | 1 |
| Third-party license allow-list, SBOM, signed artifacts | Absent (and ships an AGPL tool script) | CI · ADR-0010 | 0 / 11 |
| Customer neutrality + white-label theme | Absent (customer-looking identifiers present) | Hard rule 1; report theme | 0 / 3 |
| Shipped AI context, generated catalogs, `pataf ai sync` | Hand-written docs that drift | `_ai/`, `pataf catalog` · ADR-0008 | 10 |
| Lint suite (`pataf lint` steps/tags/locators/overrides) | Absent | `runner` | 2 / 10 |
| Packaging (wheel + extras), copier templates, runner image | Absent (script-style repo) | pyproject, `templates/`, `docker/` | 0 / 8 / 10 |
| Tests of the framework itself, typing, CI pipelines | Absent | `tests/`, mypy, `azure-pipelines.yml`, `pipelines/` | 0 |
| `pataf doctor` environment checks | Absent | `runner` | 2+ |

## 6. Proposed spec changes (proposals only; nothing changed yet)
| # | Idea from reference | Proposed change | Vehicle |
|---|---|---|---|
| P1 | `AUTH_FAILED` is a distinct triage class (`AIContext/05`, `06`) | Add `auth` to `FailureInfo.category` (REPORTING §1). It is additive, and the schema is not yet released. | Spec edit |
| P2 | Per-step "output data" in the report (`custom_json_formatter.py:183-185`) | Add `StepResult.outputs` (masked, typed key/values, e.g. a generated claim number) via `w.evidence.record(name, value)` (REPORTING §1, TYPED_AUTHORING §8 World) | Spec edit |
| P3 | `@risk:<low\|medium\|high>` tag (`AIContext/03`) | Add it to the tag taxonomy as a report filter and history dimension; enables risk-based selection (CODING_STANDARDS) | Spec edit |
| P4 | "No assertions in pages" boundary (`AIContext/01`) | TYPED_AUTHORING §3 rules: surfaces expose actions and state; assertions live in steps and flows via `expect` | Spec edit |
| P5 | Field-mapping comparison report (`Utility/HTMLReportGenerator.py`, `SubModuleReport_template.html`) | `data.files` typed field-mapping comparator (JSON/CSV ↔ fixed-width layout with positions and conditional rules) emitting typed results, plus a built-in `report_panels` panel (DRIVERS Files, REPORTING §3) | Spec edit |
| P6 | k6 and ZAP runners (`performance/`, `security/`) | New entry-point group `paccaassure_taf.importers`: convert external tool outputs (k6 summary, ZAP, JMeter) into `TestResult`s with layer `perf`/`security`. Core never bundles AGPL tools. | New ADR-0013 |
| P7 | DB access broker before connect (`db_client.StrongDMClient`) | Add a `ConnectionProvider` plugin type to `paccaassure_taf.plugins` (DRIVERS DB, ARCHITECTURE §5) for access brokers or just-in-time credentials | Spec edit (ADR if reviewers prefer) |
| P8 | HITL rules + reviewer verdict schema (`AIContext/11_AA_Stage_Lifecycle.md`, `13_*`) | AI_NATIVE §4–5: agents never request secrets and point users to `SecretRef`; add a `/review-change` recipe with a structured verdict (status, findings[rule, file, fix_hint], next step) | Spec edit |
| P9 | Resource blocking for speed (`PlayWrightClient.py:247-252`) | DRIVERS Web: `block_resources: [image, font, media]` config | Spec edit |
