import { useEffect, useState } from "preact/hooks";
import { api, ApiError, type Member, type MemberQuery, type Page, type Plan } from "../api";
import { ErrorMessage, Loading, StatusBadge } from "../components";
import { MEMBER_STATUSES, titleCase } from "../format";
import { navigate } from "../router";

const FIELDS = ["member_id", "last_name", "first_name", "date_of_birth", "status", "plan_code"] as const;
type Field = (typeof FIELDS)[number];
type Criteria = Record<Field, string>;
const PAGE_SIZES = [10, 20, 50];
export const LAST_SEARCH_KEY = "nwh.last_search";

function criteriaFrom(query: URLSearchParams): Criteria {
  return Object.fromEntries(FIELDS.map((field) => [field, query.get(field) ?? ""])) as Criteria;
}

function searchUrl(criteria: Criteria, page: number, pageSize: number): string {
  const params = new URLSearchParams();
  for (const field of FIELDS) if (criteria[field].trim()) params.set(field, criteria[field].trim());
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return `/members?${params.toString()}`;
}

export function SearchPage({ query }: { query: URLSearchParams }) {
  const applied = criteriaFrom(query);
  const searched = query.has("page");
  const page = Math.max(1, Number(query.get("page") ?? "1") || 1);
  const pageSize = PAGE_SIZES.includes(Number(query.get("page_size"))) ? Number(query.get("page_size")) : 20;
  const queryKey = query.toString();

  const [form, setForm] = useState<Criteria>(applied);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [results, setResults] = useState<Page<Member> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [memberIdError, setMemberIdError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    api.plans().then(setPlans, () => setPlans([]));
  }, []);

  useEffect(() => {
    if (!searched) {
      setResults(null);
      return;
    }
    sessionStorage.setItem(LAST_SEARCH_KEY, `/members?${queryKey}`);
    let cancelled = false;
    setLoading(true);
    setError(null);
    const request: MemberQuery = { ...applied, page, page_size: pageSize };
    api
      .searchMembers(request)
      .then((found) => !cancelled && setResults(found))
      .catch((caught: unknown) => {
        if (cancelled) return;
        setResults(null);
        setError(caught instanceof ApiError ? (caught.problem.detail ?? caught.message) : "Search failed. Try again.");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [queryKey]);

  function submit(event: Event) {
    event.preventDefault();
    const id = form.member_id.trim().toUpperCase();
    if (id && !/^NWH-M\d{6}$/.test(id)) {
      setMemberIdError("Member ID must look like NWH-M000123.");
      return;
    }
    setMemberIdError(null);
    navigate(searchUrl({ ...form, member_id: id }, 1, pageSize));
  }

  function clear() {
    setMemberIdError(null);
    sessionStorage.removeItem(LAST_SEARCH_KEY);
    navigate("/members");
  }

  async function exportCsv() {
    setExporting(true);
    try {
      const { blob, filename } = await api.exportMembers(applied);
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(link.href), 10_000);
    } catch {
      setError("Export failed. Try again.");
    } finally {
      setExporting(false);
    }
  }

  const input = (field: Field) => ({
    id: field.replaceAll("_", "-"),
    name: field,
    value: form[field],
    onInput: (event: Event) => setForm({ ...form, [field]: (event.currentTarget as HTMLInputElement).value }),
  });

  const first = results && results.total > 0 ? (results.page - 1) * results.page_size + 1 : 0;
  const last = results ? Math.min(results.page * results.page_size, results.total) : 0;

  return (
    <section>
      <h1>Member search</h1>
      <form role="search" aria-label="Member search" class="card search-form" onSubmit={submit} noValidate>
        <div class="grid">
          <div class="field">
            <label for="member-id">Member ID</label>
            <input
              {...input("member_id")}
              placeholder="NWH-M000123"
              aria-invalid={memberIdError ? "true" : undefined}
              aria-describedby={memberIdError ? "member-id-error" : undefined}
            />
            {memberIdError && (
              <p id="member-id-error" class="field-error">
                {memberIdError}
              </p>
            )}
          </div>
          <div class="field">
            <label for="last-name">Last name</label>
            <input {...input("last_name")} />
          </div>
          <div class="field">
            <label for="first-name">First name</label>
            <input {...input("first_name")} />
          </div>
          <div class="field">
            <label for="date-of-birth">Date of birth</label>
            <input {...input("date_of_birth")} type="date" />
          </div>
          <div class="field">
            <label for="status">Status</label>
            <select {...input("status")} onChange={(event) => setForm({ ...form, status: event.currentTarget.value })}>
              <option value="">Any status</option>
              {MEMBER_STATUSES.map((status) => (
                <option value={status}>{titleCase(status)}</option>
              ))}
            </select>
          </div>
          <div class="field">
            <label for="plan-code">Plan</label>
            <select {...input("plan_code")} onChange={(event) => setForm({ ...form, plan_code: event.currentTarget.value })}>
              <option value="">Any plan</option>
              {plans.map((plan) => (
                <option value={plan.plan_code}>
                  {plan.name}
                  {plan.active ? "" : " (closed)"}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div class="actions">
          <button type="submit" class="button">
            Search
          </button>
          <button type="button" class="button button-secondary" onClick={clear}>
            Clear
          </button>
        </div>
      </form>

      {error && <ErrorMessage>{error}</ErrorMessage>}
      {loading && <Loading label="Searching…" />}

      {!loading && results && (
        <section aria-label="Search results" class="results">
          <div class="results-bar">
            <p data-testid="result-summary">
              {results.total === 0 ? "No members found" : `Showing ${first}–${last} of ${results.total} members`}
            </p>
            <div class="results-tools">
              <label for="page-size">Rows per page</label>
              <select
                id="page-size"
                value={String(pageSize)}
                onChange={(event) => navigate(searchUrl(applied, 1, Number(event.currentTarget.value)))}
              >
                {PAGE_SIZES.map((size) => (
                  <option value={String(size)}>{size}</option>
                ))}
              </select>
              <button type="button" class="button button-secondary" onClick={exportCsv} disabled={exporting || results.total === 0}>
                {exporting ? "Exporting…" : "Export CSV"}
              </button>
            </div>
          </div>

          {results.total === 0 ? (
            <p class="empty" data-testid="no-results">
              No members match your search.
            </p>
          ) : (
            <table data-testid="member-results" class="table">
              <caption class="visually-hidden">Members</caption>
              <thead>
                <tr>
                  <th scope="col">Member ID</th>
                  <th scope="col">Name</th>
                  <th scope="col">Date of birth</th>
                  <th scope="col">Status</th>
                  <th scope="col">Plan</th>
                  <th scope="col">State</th>
                </tr>
              </thead>
              <tbody>
                {results.items.map((member) => (
                  <tr data-testid="member-row" data-member-id={member.member_id} key={member.member_id}>
                    <td>
                      <a href={`/members/${member.member_id}`}>{member.member_id}</a>
                    </td>
                    <td>
                      {member.last_name}, {member.first_name}
                    </td>
                    <td>{member.date_of_birth}</td>
                    <td>
                      <StatusBadge status={member.status} />
                    </td>
                    <td>{plans.find((plan) => plan.plan_code === member.plan_code)?.name ?? member.plan_code}</td>
                    <td>{member.state}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {results.total_pages > 1 && (
            <nav aria-label="Pagination" class="pagination">
              <button
                type="button"
                class="button button-secondary"
                disabled={results.page <= 1}
                onClick={() => navigate(searchUrl(applied, results.page - 1, pageSize))}
              >
                Previous page
              </button>
              <span data-testid="page-indicator">
                Page {results.page} of {results.total_pages}
              </span>
              <button
                type="button"
                class="button button-secondary"
                disabled={results.page >= results.total_pages}
                onClick={() => navigate(searchUrl(applied, results.page + 1, pageSize))}
              >
                Next page
              </button>
            </nav>
          )}
        </section>
      )}
    </section>
  );
}
