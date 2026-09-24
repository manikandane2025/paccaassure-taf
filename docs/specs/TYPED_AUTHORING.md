# Typed authoring spec (the "PaccaAssureTAF style")

Goal: a scripter or an agent can write a correct test **by following autocomplete alone**. Wrong code should fail `mypy` or `pataf lint` before it ever runs.

Code below is the **target API**. Names can be refined during build, but the principles cannot:
1. Elements are typed descriptors; each type exposes only the actions that make sense for it.
2. Surfaces (pages, screens, endpoints) declare their elements as class attributes, which makes them discoverable and catalogable.
3. Actions that navigate return the next surface type.
4. Data is pydantic models, never dicts or positional strings.
5. Steps receive a typed `World` and typed parameters.
6. Assertions are expressive, typed, and auto-waiting.

---

## 1. Locators — `By`
One driver-neutral locator vocabulary. Adapters translate it (Playwright locator, Appium strategy).
```python
from paccaassure_taf.elements import By

By.role("button", name="Search")      # web/jsp — preferred
By.label("Member ID")                 # web/jsp — preferred for inputs
By.test_id("member-search")           # web/jsp — preferred when app has data-testid
By.text("Eligibility")                # web/jsp
By.css("table#results")               # allowed, lint warns if a semantic option exists
By.xpath("//td[normalize-space()='Status']/following-sibling::td[1]")  # JSP last resort, lint requires `reason=`
By.name("memberId")                   # JSP forms
By.automation_id("txtMemberId")       # desktop (UIA AutomationId)
By.accessibility_id("Save")           # desktop
```
Chaining and scoping: `By.test_id("results").within(By.role("row", name=...))`.
Frames (JSP): `By.name("memberId").in_frame("mainFrame")`.

## 2. Typed elements
```python
from paccaassure_taf.elements import (Button, TextInput, SecretInput, Checkbox, Radio, Dropdown,
                          DatePicker, Link, Label, Table, Grid, FileUpload, Tabs, Dialog)

class Status(StrEnum):
    ACTIVE = "Active"
    TERMINATED = "Terminated"

status_filter = Dropdown[Status](By.label("Status"))   # .select(Status.ACTIVE) — typos impossible
member_id     = TextInput(By.label("Member ID"))        # .fill(str) .clear() .value() — no .click()
password      = SecretInput(By.label("Password"))       # accepts SecretStr only, never logged
search        = Button(By.role("button", name="Search"))# .click() .is_enabled() — no .fill()
results       = Table[MemberRow](By.test_id("results")) # .rows() -> list[MemberRow], .row_where(...)
```
`Table[T]` maps header text → pydantic fields (`Field(alias="Member ID")`) and returns typed rows. Same class works for JSP HTML tables and desktop grids (adapter-specific readers).

Every element supports `expect` (see §7), `.is_visible()`, and `.describe()` (used in logs/evidence as a human name derived from the attribute name, e.g. `MemberSearchPage.member_id`).

## 3. Components and pages
```python
from typing import ClassVar
from paccaassure_taf.web import WebPage, WebComponent

class HeaderNav(WebComponent):
    root = By.role("navigation", name="Main")
    members = Link(By.text("Members"))
    user_menu = Button(By.test_id("user-menu"))

class MemberSearchPage(WebPage):
    route: ClassVar[str] = "/members/search"       # used by open() and URL assertions
    title: ClassVar[str] = "Member Search"         # used by is_loaded()
    header = HeaderNav()
    member_id = TextInput(By.label("Member ID"))
    status = Dropdown[Status](By.label("Status"))
    search_btn = Button(By.role("button", name="Search"))
    results = Table[MemberRow](By.test_id("results"))

    def search(self, criteria: MemberSearchCriteria) -> "MemberSearchPage":
        """Fill criteria and search. Stays on this page.

        Example:
            page.search(MemberSearchCriteria(member_id=MemberId("M0001")))
        """
        self.member_id.fill(criteria.member_id)
        if criteria.status:
            self.status.select(criteria.status)
        self.search_btn.click()
        return self

    def open_member(self, member_id: MemberId) -> "MemberDetailPage":
        self.results.row_where(member_id=member_id).click()
        return self.go(MemberDetailPage)            # waits for is_loaded(); returns typed page
```
Rules: no locator strings inside methods; methods do **one surface's** work; navigation returns a page type; methods have docstrings with an example.
**Surfaces expose actions and state, never assertions.** A page method may return a value (`status_label.text()`, `is_loaded()`), but pass/fail decisions live in steps and flows via `expect`, so every assertion gets the same auto-wait, soft-mode, masking and evidence handling.

## 4. JSP pages, desktop screens, API endpoints — same shape
```python
class LegacyEligibilityPage(JspPage):                 # paccaassure_taf.jsp
    frame: ClassVar[str] = "contentFrame"             # default frame for all elements
    member_id = TextInput(By.name("memberId"))
    submit = Button(By.role("button", name="Find"), postback=True)  # waits for full reload

class ClaimEntryScreen(DesktopScreen):                # paccaassure_taf.desktop
    window_title: ClassVar[str] = "Claim Entry"
    claim_no = TextInput(By.automation_id("txtClaimNo"))
    save = Button(By.accessibility_id("Save"))

class GetMember(Endpoint[None, Member]):              # paccaassure_taf.api
    method: ClassVar[HttpMethod] = HttpMethod.GET     # enum, never a raw string
    path: ClassVar[str] = "/api/v1/members/{member_id}"

class MemberApi(ApiClient):
    def get_member(self, member_id: MemberId) -> Member:
        return self.call(GetMember, path_params={"member_id": member_id})
```
`Endpoint[Req, Resp]` validates request/response with pydantic; `.call_raw()` returns a typed `ApiResponse[Resp]` for negative tests (status, headers, errors, timing).

## 5. Data models
```python
from paccaassure_taf.data import Sensitive, TestData, factory   # Sensitive is defined in core.masking, re-exported here

MemberId = NewType("MemberId", str)

class Member(TestData):
    member_id: MemberId
    first_name: Sensitive[str]              # masked in logs/reports
    dob: Sensitive[date]
    plan: PlanCode                          # enum
    status: Status

@factory(Member)
def active_member(seed: int) -> Member: ...          # synthetic, never real PHI; deterministic per seed

variant = active_member(seed=7).model_copy(update={"status": Status.TERMINATED})  # typed overrides, no Any

# Profiles: data/profiles/<env>.yaml, typed by model, resolved by key
member = world.data.get(Member, "active_adult")      # returns Member
```
DB checks: `Query[Row]` with SQL in `.sql` files, named binds, typed rows:
```python
class EligibilityRow(Row): member_id: MemberId; start_date: date; end_date: date | None
ELIG_BY_MEMBER = Query[EligibilityRow].from_file("sql/eligibility_by_member.sql")
rows = world.db("claims").fetch(ELIG_BY_MEMBER, member_id=member.member_id)
```

## 6. Flows (business tasks)
```python
class EligibilityFlows(Flow):
    def verify_member_active(self, member: Member) -> MemberDetailPage:
        return (self.app.open(MemberSearchPage)
                .search(MemberSearchCriteria(member_id=member.member_id))
                .open_member(member.member_id))
```
`self.app` resolves pages through the override registry (see LAYERING.md), so variant overrides apply automatically.

## 7. Assertions — `expect`
Auto-waiting, typed, evidence-aware:
```python
expect(page.results).to_have_row_count(1)
expect(page.results).to_contain_row(member_id=member.member_id, status=Status.ACTIVE)
expect(detail.status_label).to_have_text(Status.ACTIVE)
expect(response).to_have_status(200).and_body_matches(Member)
expect(rows).to_equal_ignoring_order(expected_rows)
soft = expect.soft()          # collect several failures, raise at scenario end
```
Failure messages name the element (`MemberSearchPage.results`), the expectation, actual vs expected (masked), and link the evidence.

## 8. Typed BDD steps
```python
from paccaassure_taf.bdd import given, when, then, World, Table

# northwind_claims/world.py — the app pack declares its scenario store once and exports an alias
@dataclass
class ClaimsScenario:
    member: Member | None = None

ClaimsWorld = World[ClaimsScenario]

@given("an {member} member exists")                   # type comes from the annotation, not the pattern
def _(w: ClaimsWorld, member: MemberRef) -> None:
    w.scenario.member = w.data.get(Member, member)

@when("the {role} searches for that member")
def _(w: ClaimsWorld, role: UserRole) -> None:
    w.flows(EligibilityFlows).login_as(role).search_member(w.scenario.member)

@then("the results show")
def _(w: ClaimsWorld, table: Table[MemberRow]) -> None:   # Gherkin table → typed rows
    expect(w.page(MemberSearchPage).results).to_contain_rows(table.rows)
```
- `World[S]` is a typed facade, generic over the scenario store `S`: `w.config`, `w.data`, `w.app` (web/jsp), `w.api(MemberApi)`, `w.desktop`, `w.db(name)`, `w.flows(T)`, `w.page(T)`, `w.evidence`, and `w.scenario: S` (a typed per-scenario store; each app pack declares its schema as a dataclass and exports an alias such as `ClaimsWorld`). How a variant suite combines stores from several app packs is finalized in Phase 2 (ADR-0002 amendment).
- `w.evidence.record(name, value)` records a step **output** (e.g. a generated claim number) into `StepResult.outputs`; values pass through masking like everything else.
- Parse types come from annotations: any `StrEnum`, `NewType` id, `date`, `Decimal`, and registered types (`MemberRef`, `UserRole`). Patterns use bare `{name}` placeholders; the type is taken from the parameter annotation (single source of truth). No manual `register_type`; `pataf lint steps` fails if a placeholder has no matching annotated parameter.
- Duplicate or overlapping step patterns fail `pataf lint steps`.
- Step phrasing follows the catalog's controlled vocabulary (docs/conventions).

## 9. Feature files
```gherkin
@app:claims @variant:state-ga @smoke @tms:ADO-48213 @req:ELIG-012
Feature: Member eligibility search
  Scenario: Active member is found by ID
    Given an active adult member exists
    When the eligibility worker searches for that member
    Then the results show
      | Member ID                  | Status |
      | ${member.member_id}        | Active |
```
Tag taxonomy is validated (conventions doc). `${member.member_id}` references scenario data (`w.scenario.member.member_id`), resolved by the typed table. The `${…}` syntax is deliberately distinct from Behave's Scenario Outline `<placeholder>` substitution, so both can be used in one feature.

## 10. What makes this AI-friendly (keep it that way)
- Discoverability: everything is a class attribute or typed method, so the catalog generator can list it.
- Narrow surfaces: an agent can't call an invalid action, and mypy says why.
- Single obvious place for each kind of code (layer table).
- Docstring examples are copy-paste ready and verified by doctest-style checks in CI where feasible.
