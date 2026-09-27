// Typed client for the Northwind Health sandbox API (proxied at /api by nginx and the Vite dev server).
import { clearSession, getSession } from "./session";

export type Role = "ADMIN" | "EXAMINER" | "VIEWER";
export type MemberStatus = "ACTIVE" | "INACTIVE" | "SUSPENDED" | "PENDING";
export type ClaimStatus = "SUBMITTED" | "IN_REVIEW" | "APPROVED" | "DENIED" | "PAID";

export interface Token {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  role: Role;
  display_name: string;
}

export interface Plan {
  plan_code: string;
  name: string;
  tier: "BRONZE" | "SILVER" | "GOLD" | "PLATINUM";
  monthly_premium: number;
  deductible: number;
  active: boolean;
  description: string;
}

export interface Member {
  member_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  ssn: string;
  email: string;
  phone: string;
  address_line: string;
  city: string;
  state: string;
  postal_code: string;
  status: MemberStatus;
  plan_code: string;
  enrolled_on: string;
  version: number;
  updated_at: string;
}

export type MemberUpdate = Pick<
  Member,
  "email" | "phone" | "address_line" | "city" | "state" | "postal_code" | "status" | "plan_code" | "version"
>;

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface Claim {
  claim_id: string;
  member_id: string;
  external_ref: string;
  service_date: string;
  submitted_at: string;
  provider_name: string;
  diagnosis_code: string;
  amount: number;
  status: ClaimStatus;
  notes: string;
}

export interface FieldError {
  field: string;
  message: string;
  type: string;
}

export interface Problem {
  type: string;
  title: string;
  status: number;
  detail?: string;
  errors?: FieldError[];
}

export class ApiError extends Error {
  constructor(readonly problem: Problem) {
    super(problem.detail ?? problem.title);
  }
  get status(): number {
    return this.problem.status;
  }
}

/** Fired when the API rejects the session token (expired or invalid); the app sends the user to sign in. */
export const SESSION_EXPIRED_EVENT = "nwh:session-expired";

const DELAY_KEY = "nwh.delay_ms";

/** `?delay_ms=N` on any page slows every API call by N ms for the rest of the tab session (wait tests). */
export function captureDelayFromUrl(): void {
  const value = new URLSearchParams(window.location.search).get("delay_ms");
  if (value === null) return;
  if (/^\d+$/.test(value) && Number(value) > 0) sessionStorage.setItem(DELAY_KEY, value);
  else sessionStorage.removeItem(DELAY_KEY);
}

type Query = Record<string, string | number | undefined>;

function url(path: string, query: Query = {}): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const delay = sessionStorage.getItem(DELAY_KEY);
  if (delay) params.set("delay_ms", delay);
  const text = params.toString();
  return `/api${path}${text ? `?${text}` : ""}`;
}

async function request(method: string, path: string, options: { query?: Query; body?: unknown; auth?: boolean } = {}): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const session = getSession();
  if (options.auth !== false && session) headers.Authorization = `Bearer ${session.token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(url(path, options.query), {
    method,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (response.ok) return response;
  let problem: Problem;
  try {
    problem = (await response.json()) as Problem;
  } catch {
    problem = { type: "about:blank", title: response.statusText, status: response.status };
  }
  if (response.status === 401 && options.auth !== false) {
    clearSession();
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }
  throw new ApiError(problem);
}

async function json<T>(method: string, path: string, options: { query?: Query; body?: unknown; auth?: boolean } = {}): Promise<T> {
  return (await (await request(method, path, options)).json()) as T;
}

export interface MemberQuery {
  member_id?: string;
  last_name?: string;
  first_name?: string;
  date_of_birth?: string;
  status?: string;
  plan_code?: string;
  page?: number;
  page_size?: number;
}

export const api = {
  login: (username: string, password: string) =>
    json<Token>("POST", "/auth/token", { body: { username, password }, auth: false }),
  plans: () => json<Plan[]>("GET", "/plans", { auth: false }),
  plan: (code: string) => json<Plan>("GET", `/plans/${encodeURIComponent(code)}`, { auth: false }),
  searchMembers: (query: MemberQuery) => json<Page<Member>>("GET", "/members", { query: { ...query } }),
  member: (id: string) => json<Member>("GET", `/members/${encodeURIComponent(id)}`),
  memberClaims: (id: string) => json<Claim[]>("GET", `/members/${encodeURIComponent(id)}/claims`),
  updateMember: (id: string, update: MemberUpdate) =>
    json<Member>("PUT", `/members/${encodeURIComponent(id)}`, { body: update }),
  exportMembers: async (query: MemberQuery): Promise<{ blob: Blob; filename: string }> => {
    const { page: _page, page_size: _size, ...filters } = query;
    const response = await request("GET", "/members/export.csv", { query: { ...filters } });
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "members.csv";
    return { blob: await response.blob(), filename };
  },
};
