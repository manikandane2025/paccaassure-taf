import type { ComponentChildren } from "preact";
import { useEffect, useState } from "preact/hooks";
import type { ClaimStatus, MemberStatus } from "./api";
import { titleCase } from "./format";

export function StatusBadge({ status }: { status: MemberStatus | ClaimStatus }) {
  return (
    <span class={`badge badge-${status.toLowerCase().replace("_", "-")}`} data-testid="status-badge">
      {titleCase(status)}
    </span>
  );
}

// Flash messages survive one navigation (e.g. "Member updated." shown on the detail page after saving).
let flashMessage: string | null = null;
const listeners = new Set<(message: string | null) => void>();

export function flash(message: string): void {
  flashMessage = message;
  listeners.forEach((listener) => listener(message));
}

export function Toast() {
  const [message, setMessage] = useState<string | null>(flashMessage);
  useEffect(() => {
    listeners.add(setMessage);
    return () => listeners.delete(setMessage);
  }, []);
  useEffect(() => {
    if (message === null) return;
    const timer = window.setTimeout(() => {
      flashMessage = null;
      setMessage(null);
    }, 6000);
    return () => window.clearTimeout(timer);
  }, [message]);
  if (!message) return null;
  return (
    <div class="toast" role="status" aria-live="polite" data-testid="toast">
      <span>{message}</span>
      <button
        type="button"
        class="link-button"
        aria-label="Dismiss message"
        onClick={() => {
          flashMessage = null;
          setMessage(null);
        }}
      >
        ×
      </button>
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <p class="loading" role="status" aria-live="polite" data-testid="loading">
      <span class="spinner" aria-hidden="true" />
      {label}
    </p>
  );
}

export function ErrorMessage({ children }: { children: ComponentChildren }) {
  return (
    <div class="alert alert-error" role="alert">
      {children}
    </div>
  );
}
