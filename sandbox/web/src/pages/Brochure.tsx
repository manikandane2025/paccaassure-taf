// Public plan brochure: opened in a new tab from the member Plan tab (new-page / popup handling tests).
import { useEffect, useState } from "preact/hooks";
import { api, type Plan } from "../api";
import { ErrorMessage, Loading } from "../components";
import { money } from "../format";

export function BrochurePage({ code }: { code: string }) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.plan(code).then(
      (found) => {
        setPlan(found);
        document.title = `${found.name} brochure · Northwind Health`;
      },
      () => setError(`Plan ${code} was not found.`),
    );
  }, [code]);

  if (error) return <ErrorMessage>{error}</ErrorMessage>;
  if (!plan) return <Loading label="Loading brochure…" />;
  return (
    <article class="card brochure" data-testid="plan-brochure">
      <p class="muted">Plan brochure</p>
      <h1>{plan.name}</h1>
      <p>{plan.description}</p>
      <dl class="details">
        <dt>Plan code</dt>
        <dd>{plan.plan_code}</dd>
        <dt>Tier</dt>
        <dd>{plan.tier}</dd>
        <dt>Monthly premium</dt>
        <dd>{money(plan.monthly_premium)}</dd>
        <dt>Deductible</dt>
        <dd>{money(plan.deductible)}</dd>
        <dt>Enrollment</dt>
        <dd>{plan.active ? "Open" : "Closed to new members"}</dd>
      </dl>
    </article>
  );
}
