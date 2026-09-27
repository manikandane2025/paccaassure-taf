import type { JSX } from "preact";
import { useEffect, useState } from "preact/hooks";
import { api, ApiError, type Member, type MemberStatus, type MemberUpdate, type Plan } from "../api";
import { ErrorMessage, flash, Loading } from "../components";
import { MEMBER_STATUSES, STATES, titleCase } from "../format";
import { navigate } from "../router";
import { canEdit, getSession } from "../session";

type FormField = Exclude<keyof MemberUpdate, "version">;
type Errors = Partial<Record<FormField, string>>;

const LABELS: Record<FormField, string> = {
  email: "Email",
  phone: "Phone",
  address_line: "Address",
  city: "City",
  state: "State",
  postal_code: "Postal code",
  status: "Status",
  plan_code: "Plan",
};

function validate(form: MemberUpdate): Errors {
  const errors: Errors = {};
  if (!form.email.trim()) errors.email = "Enter an email address.";
  else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) errors.email = "Enter a valid email address, like name@example.com.";
  if (!/^\d{3}-\d{3}-\d{4}$/.test(form.phone.trim())) errors.phone = "Enter the phone number as 404-555-0123.";
  if (!form.address_line.trim()) errors.address_line = "Enter the street address.";
  if (!form.city.trim()) errors.city = "Enter the city.";
  if (!/^\d{5}$/.test(form.postal_code.trim())) errors.postal_code = "Enter a 5-digit postal code.";
  return errors;
}

function fromMember(member: Member): MemberUpdate {
  const { email, phone, address_line, city, state, postal_code, status, plan_code, version } = member;
  return { email, phone, address_line, city, state, postal_code, status, plan_code, version };
}

export function EditPage({ memberId }: { memberId: string }) {
  const [member, setMember] = useState<Member | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [form, setForm] = useState<MemberUpdate | null>(null);
  const [errors, setErrors] = useState<Errors>({});
  const [problem, setProblem] = useState<{ message: string; conflict: boolean } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.member(memberId), api.plans()])
      .then(([found, allPlans]) => {
        if (cancelled) return;
        setMember(found);
        setForm(fromMember(found));
        setPlans(allPlans.filter((plan) => plan.active || plan.plan_code === found.plan_code));
        setErrors({});
        setProblem(null);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setLoadError(caught instanceof ApiError ? (caught.problem.detail ?? caught.message) : "The member could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [memberId, reloadKey]);

  if (!canEdit(getSession())) {
    return (
      <section>
        <h1>Edit member</h1>
        <ErrorMessage>You don't have permission to edit members.</ErrorMessage>
        <a href={`/members/${memberId}`}>Back to member</a>
      </section>
    );
  }
  if (loadError) {
    return (
      <section>
        <h1>Edit member</h1>
        <ErrorMessage>{loadError}</ErrorMessage>
        <a href="/members">Back to search</a>
      </section>
    );
  }
  if (!member || !form) return <Loading label="Loading member…" />;

  const set = (field: FormField, value: string) => setForm({ ...form, [field]: value });

  async function submit(event: Event) {
    event.preventDefault();
    if (!form || !member) return;
    const found = validate(form);
    setErrors(found);
    setProblem(null);
    if (Object.keys(found).length > 0) {
      document.getElementById("error-summary")?.focus();
      return;
    }
    setSaving(true);
    try {
      const trimmed: MemberUpdate = { ...form, email: form.email.trim(), phone: form.phone.trim(), address_line: form.address_line.trim(), city: form.city.trim(), postal_code: form.postal_code.trim() };
      await api.updateMember(member.member_id, trimmed);
      flash("Member updated.");
      navigate(`/members/${member.member_id}`);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        setProblem({ message: "Someone else changed this member while you were editing. Reload to see the latest version.", conflict: true });
      } else if (caught instanceof ApiError && caught.problem.errors?.length) {
        const serverErrors: Errors = {};
        for (const error of caught.problem.errors) {
          const field = error.field.split(".").pop() as FormField;
          if (field in LABELS) serverErrors[field] = error.message;
        }
        setErrors(serverErrors);
        setProblem({ message: caught.problem.detail ?? "The server rejected the changes.", conflict: false });
      } else {
        setProblem({ message: caught instanceof ApiError ? (caught.problem.detail ?? caught.message) : "Saving failed. Try again.", conflict: false });
      }
    } finally {
      setSaving(false);
    }
  }

  const errorCount = Object.keys(errors).length;
  const field = (name: FormField, control: JSX.Element) => (
    <div class={errors[name] ? "field field-invalid" : "field"}>
      <label for={`edit-${name.replaceAll("_", "-")}`}>{LABELS[name]}</label>
      {control}
      {errors[name] && (
        <p id={`edit-${name.replaceAll("_", "-")}-error`} class="field-error">
          {errors[name]}
        </p>
      )}
    </div>
  );
  const textProps = (name: FormField) => ({
    id: `edit-${name.replaceAll("_", "-")}`,
    name,
    value: form[name],
    "aria-invalid": errors[name] ? ("true" as const) : undefined,
    "aria-describedby": errors[name] ? `edit-${name.replaceAll("_", "-")}-error` : undefined,
    onInput: (event: Event) => set(name, (event.currentTarget as HTMLInputElement).value),
  });

  return (
    <section>
      <h1>Edit member</h1>
      <p class="muted">
        {member.first_name} {member.last_name} · {member.member_id}
      </p>

      {errorCount > 0 && (
        <div id="error-summary" class="alert alert-error" role="alert" tabIndex={-1} data-testid="error-summary">
          <p>
            Fix {errorCount} {errorCount === 1 ? "problem" : "problems"} to continue:
          </p>
          <ul>
            {(Object.keys(errors) as FormField[]).map((name) => (
              <li>
                <a href={`#edit-${name.replaceAll("_", "-")}`}>{errors[name]}</a>
              </li>
            ))}
          </ul>
        </div>
      )}
      {problem && (
        <ErrorMessage>
          <p>{problem.message}</p>
          {problem.conflict && (
            <button type="button" class="button button-secondary" onClick={() => setReloadKey((key) => key + 1)}>
              Reload
            </button>
          )}
        </ErrorMessage>
      )}

      <form aria-label="Edit member" class="card" onSubmit={submit} noValidate>
        <div class="grid">
          {field("email", <input {...textProps("email")} type="email" autocomplete="off" />)}
          {field("phone", <input {...textProps("phone")} type="tel" placeholder="404-555-0123" />)}
          {field("address_line", <input {...textProps("address_line")} />)}
          {field("city", <input {...textProps("city")} />)}
          {field(
            "state",
            <select {...textProps("state")} onChange={(event) => set("state", event.currentTarget.value)}>
              {[...new Set([...STATES, member.state])].sort().map((state) => (
                <option value={state}>{state}</option>
              ))}
            </select>,
          )}
          {field("postal_code", <input {...textProps("postal_code")} inputMode="numeric" />)}
          {field(
            "status",
            <select {...textProps("status")} onChange={(event) => set("status", event.currentTarget.value as MemberStatus)}>
              {MEMBER_STATUSES.map((status) => (
                <option value={status}>{titleCase(status)}</option>
              ))}
            </select>,
          )}
          {field(
            "plan_code",
            <select {...textProps("plan_code")} onChange={(event) => set("plan_code", event.currentTarget.value)}>
              {plans.map((plan) => (
                <option value={plan.plan_code}>
                  {plan.name}
                  {plan.active ? "" : " (closed)"}
                </option>
              ))}
            </select>,
          )}
        </div>
        <div class="actions">
          <button type="submit" class="button" disabled={saving}>
            {saving ? "Saving…" : "Save changes"}
          </button>
          <a class="button button-secondary" href={`/members/${member.member_id}`}>
            Cancel
          </a>
        </div>
      </form>
    </section>
  );
}
