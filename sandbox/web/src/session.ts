// Signed-in user, per browser tab (sessionStorage): each Playwright context or tab signs in on its own.
import type { Role, Token } from "./api";

export interface Session {
  token: string;
  role: Role;
  displayName: string;
  expiresAt: number;
}

const KEY = "nwh.session";

export function getSession(): Session | null {
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}

export function saveSession(token: Token): Session {
  const session: Session = {
    token: token.access_token,
    role: token.role,
    displayName: token.display_name,
    expiresAt: Date.now() + token.expires_in * 1000,
  };
  sessionStorage.setItem(KEY, JSON.stringify(session));
  return session;
}

export function clearSession(): void {
  sessionStorage.removeItem(KEY);
}

export function canEdit(session: Session | null): boolean {
  return session?.role === "ADMIN" || session?.role === "EXAMINER";
}
