import { useState } from "preact/hooks";
import { api, ApiError } from "../api";
import { navigate } from "../router";
import { saveSession } from "../session";

function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") && !value.startsWith("/login") ? value : "/members";
}

export function LoginPage({ query }: { query: URLSearchParams }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const notice = query.has("expired")
    ? "Your session has expired. Please sign in again."
    : query.has("signed_out")
      ? "You have signed out."
      : null;

  async function submit(event: Event) {
    event.preventDefault();
    if (!username.trim() || !password) {
      setError("Enter your username and password.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      saveSession(await api.login(username.trim(), password));
      navigate(safeNext(query.get("next")), { replace: true });
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 423) setError("Your account is locked. Contact your administrator.");
      else if (caught instanceof ApiError && caught.status === 401) setError("Invalid username or password.");
      else setError("Sign-in is unavailable. Try again later.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section class="card narrow">
      <h1>Sign in</h1>
      {notice && (
        <p class="alert alert-info" role="status" data-testid="login-notice">
          {notice}
        </p>
      )}
      <form aria-label="Sign in" onSubmit={submit} noValidate>
        <div class="field">
          <label for="username">Username</label>
          <input
            id="username"
            name="username"
            autocomplete="username"
            value={username}
            onInput={(event) => setUsername(event.currentTarget.value)}
          />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autocomplete="current-password"
            value={password}
            onInput={(event) => setPassword(event.currentTarget.value)}
          />
        </div>
        {error && (
          <p class="alert alert-error" role="alert" data-testid="login-error">
            {error}
          </p>
        )}
        <button type="submit" class="button" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </section>
  );
}
