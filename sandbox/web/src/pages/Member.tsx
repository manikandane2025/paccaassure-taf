import { useEffect, useRef, useState } from "preact/hooks";
import { api, ApiError, type Claim, type Member, type Plan } from "../api";
import { ErrorMessage, flash, Loading, StatusBadge } from "../components";
import { maskSsn, money, timestamp } from "../format";
import { navigate } from "../router";
import { canEdit, getSession } from "../session";
import { LAST_SEARCH_KEY } from "./Search";

const TABS = ["overview", "claims", "plan"] as const;
type Tab = (typeof TABS)[number];

export function MemberPage({ memberId, query }: { memberId: string; query: URLSearchParams }) {
  const [member, setMember] = useState<Member | null>(null);
  const [claims, setClaims] = useState<Claim[] | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<{ status: number; message: string } | null>(null);
  const [revealSsn, setRevealSsn] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const requested = query.get("tab");
  const tab: Tab = (TABS as readonly string[]).includes(requested ?? "") ? (requested as Tab) : "overview";

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setMember(null);
    setClaims(null);
    Promise.all([api.member(memberId), api.memberClaims(memberId)])
      .then(async ([found, foundClaims]) => {
        if (cancelled) return;
        setMember(found);
        setClaims(foundClaims);
        const foundPlan = await api.plan(found.plan_code).catch(() => null);
        if (!cancelled) setPlan(foundPlan);
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        if (caught instanceof ApiError) setError({ status: caught.status, message: caught.problem.detail ?? caught.message });
        else setError({ status: 0, message: "The member could not be loaded." });
      });
    return () => {
      cancelled = true;
    };
  }, [memberId, reloadKey]);

  const backLink = sessionStorage.getItem(LAST_SEARCH_KEY) ?? "/members";

  if (error) {
    return (
      <section>
        <h1>{error.status === 404 ? "Member not found" : "Something went wrong"}</h1>
        <ErrorMessage>{error.message}</ErrorMessage>
        <a href={backLink}>Back to search results</a>
      </section>
    );
  }
  if (!member || !claims) return <Loading label="Loading member…" />;

  const editable = canEdit(getSession());
  const selectTab = (next: Tab) => navigate(`/members/${member.member_id}${next === "overview" ? "" : `?tab=${next}`}`, { replace: true });

  return (
    <section>
      <p>
        <a href={backLink}>← Back to search results</a>
      </p>
      <div class="member-header">
        <div>
          <h1 data-testid="member-name">
            {member.first_name} {member.last_name}
          </h1>
          <p class="muted">
            <span data-testid="member-id">{member.member_id}</span> · <StatusBadge status={member.status} />
          </p>
        </div>
        {editable && (
          <div class="actions">
            <a class="button" href={`/members/${member.member_id}/edit`}>
              Edit member
            </a>
            {member.status !== "INACTIVE" && <DeactivateButton member={member} onDone={() => setReloadKey((key) => key + 1)} />}
          </div>
        )}
      </div>

      <Tabs selected={tab} onSelect={selectTab} labels={{ overview: "Overview", claims: `Claims (${claims.length})`, plan: "Plan" }} />

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} class="card" tabIndex={0}>
        {tab === "overview" && (
          <dl class="details" data-testid="member-overview">
            <dt>Member ID</dt>
            <dd>{member.member_id}</dd>
            <dt>Date of birth</dt>
            <dd>{member.date_of_birth}</dd>
            <dt>SSN</dt>
            <dd>
              <span data-testid="member-ssn">{revealSsn ? member.ssn : maskSsn(member.ssn)}</span>{" "}
              <button type="button" class="link-button" aria-pressed={revealSsn} onClick={() => setRevealSsn(!revealSsn)}>
                {revealSsn ? "Hide SSN" : "Show SSN"}
              </button>
            </dd>
            <dt>Email</dt>
            <dd>{member.email}</dd>
            <dt>Phone</dt>
            <dd>{member.phone}</dd>
            <dt>Address</dt>
            <dd>
              {member.address_line}, {member.city}, {member.state} {member.postal_code}
            </dd>
            <dt>Status</dt>
            <dd>
              <StatusBadge status={member.status} />
            </dd>
            <dt>Plan</dt>
            <dd>{plan ? `${plan.name} (${plan.plan_code})` : member.plan_code}</dd>
            <dt>Enrolled on</dt>
            <dd>{member.enrolled_on}</dd>
            <dt>Last updated</dt>
            <dd>{timestamp(member.updated_at)}</dd>
          </dl>
        )}

        {tab === "claims" &&
          (claims.length === 0 ? (
            <p class="empty" data-testid="no-claims">
              This member has no claims.
            </p>
          ) : (
            <table class="table" data-testid="claims-table">
              <caption class="visually-hidden">Claims</caption>
              <thead>
                <tr>
                  <th scope="col">Claim ID</th>
                  <th scope="col">Service date</th>
                  <th scope="col">Provider</th>
                  <th scope="col">Diagnosis</th>
                  <th scope="col" class="numeric">
                    Amount
                  </th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {claims.map((claim) => (
                  <tr data-testid="claim-row" data-claim-id={claim.claim_id} key={claim.claim_id}>
                    <td>{claim.claim_id}</td>
                    <td>{claim.service_date}</td>
                    <td>{claim.provider_name}</td>
                    <td>{claim.diagnosis_code}</td>
                    <td class="numeric">{money(claim.amount)}</td>
                    <td>
                      <StatusBadge status={claim.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}

        {tab === "plan" &&
          (plan ? (
            <div data-testid="member-plan">
              <h2>{plan.name}</h2>
              <dl class="details">
                <dt>Plan code</dt>
                <dd>{plan.plan_code}</dd>
                <dt>Tier</dt>
                <dd>{plan.tier}</dd>
                <dt>Monthly premium</dt>
                <dd>{money(plan.monthly_premium)}</dd>
                <dt>Deductible</dt>
                <dd>{money(plan.deductible)}</dd>
              </dl>
              <p>
                <a href={`/plans/${plan.plan_code}`} target="_blank" rel="noopener">
                  Open plan brochure
                </a>{" "}
                <span class="muted">(opens in a new tab)</span>
              </p>
            </div>
          ) : (
            <Loading label="Loading plan…" />
          ))}
      </div>
    </section>
  );
}

function Tabs({ selected, onSelect, labels }: { selected: Tab; onSelect: (tab: Tab) => void; labels: Record<Tab, string> }) {
  function onKeyDown(event: KeyboardEvent) {
    const index = TABS.indexOf(selected);
    const next = event.key === "ArrowRight" ? index + 1 : event.key === "ArrowLeft" ? index - 1 : null;
    if (next === null) return;
    event.preventDefault();
    const tab = TABS[(next + TABS.length) % TABS.length] ?? "overview";
    onSelect(tab);
    document.getElementById(`tab-${tab}`)?.focus();
  }
  return (
    <div role="tablist" aria-label="Member sections" class="tabs" onKeyDown={onKeyDown}>
      {TABS.map((tab) => (
        <button
          type="button"
          role="tab"
          id={`tab-${tab}`}
          aria-selected={tab === selected}
          aria-controls={`panel-${tab}`}
          tabIndex={tab === selected ? 0 : -1}
          class={tab === selected ? "tab tab-selected" : "tab"}
          onClick={() => onSelect(tab)}
        >
          {labels[tab]}
        </button>
      ))}
    </div>
  );
}

function DeactivateButton({ member, onDone }: { member: Member; onDone: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      const { email, phone, address_line, city, state, postal_code, plan_code, version } = member;
      await api.updateMember(member.member_id, { email, phone, address_line, city, state, postal_code, plan_code, version, status: "INACTIVE" });
      dialog.current?.close();
      flash("Member deactivated.");
      onDone();
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status === 409
          ? "Someone else changed this member. Close this dialog and reload."
          : caught instanceof ApiError
            ? (caught.problem.detail ?? caught.message)
            : "The member could not be deactivated.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        class="button button-danger"
        onClick={() => {
          setError(null);
          dialog.current?.showModal();
        }}
      >
        Deactivate member
      </button>
      <dialog ref={dialog} aria-labelledby="deactivate-title" aria-describedby="deactivate-text" data-testid="deactivate-dialog">
        <h2 id="deactivate-title">Deactivate member?</h2>
        <p id="deactivate-text">
          {member.first_name} {member.last_name} ({member.member_id}) will no longer be able to submit claims.
        </p>
        {error && <ErrorMessage>{error}</ErrorMessage>}
        <div class="actions">
          <button type="button" class="button button-danger" onClick={confirm} disabled={busy}>
            {busy ? "Deactivating…" : "Deactivate"}
          </button>
          <button type="button" class="button button-secondary" onClick={() => dialog.current?.close()} disabled={busy}>
            Cancel
          </button>
        </div>
      </dialog>
    </>
  );
}
