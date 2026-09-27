import { render } from "preact";
import { useEffect } from "preact/hooks";
import { captureDelayFromUrl, SESSION_EXPIRED_EVENT } from "./api";
import { Toast } from "./components";
import { BrochurePage } from "./pages/Brochure";
import { EditPage } from "./pages/Edit";
import { LoginPage } from "./pages/Login";
import { MemberPage } from "./pages/Member";
import { SearchPage } from "./pages/Search";
import { match, navigate, onLinkClick, useLocation } from "./router";
import { clearSession, getSession } from "./session";
import "./styles.css";

captureDelayFromUrl();

function Header() {
  const session = getSession();
  return (
    <header class="app-header">
      <a class="brand" href={session ? "/members" : "/login"}>
        <span class="brand-mark" aria-hidden="true">
          NW
        </span>
        Northwind Health
      </a>
      {session && (
        <nav aria-label="Main">
          <a href="/members">Members</a>
        </nav>
      )}
      {session && (
        <div class="user">
          <span data-testid="current-user">
            {session.displayName} <span class="role">({session.role})</span>
          </span>
          <button
            type="button"
            class="button button-secondary"
            onClick={() => {
              clearSession();
              navigate("/login?signed_out=1");
            }}
          >
            Sign out
          </button>
        </div>
      )}
    </header>
  );
}

function NotFound() {
  return (
    <section>
      <h1>Page not found</h1>
      <p>
        <a href="/members">Go to member search</a>
      </p>
    </section>
  );
}

function App() {
  const location = useLocation();
  const { path } = location;

  useEffect(() => {
    const expired = () => {
      // Parallel requests can each get a 401: redirect once, keeping the original page as `next`.
      if (window.location.pathname === "/login") return;
      const here = window.location.pathname + window.location.search;
      navigate(`/login?expired=1&next=${encodeURIComponent(here)}`, { replace: true });
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, expired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, expired);
  }, []);

  const brochure = match("/plans/:code", path);
  const isPublic = path === "/login" || brochure !== null;
  const session = getSession();

  useEffect(() => {
    if (path === "/") navigate(session ? "/members" : "/login", { replace: true });
    else if (!isPublic && !session) {
      navigate(`/login?next=${encodeURIComponent(path + window.location.search)}`, { replace: true });
    }
  }, [path, isPublic, session]);

  let page;
  const edit = match("/members/:id/edit", path);
  const detail = match("/members/:id", path);
  if (path === "/login") page = <LoginPage query={location.query} />;
  else if (brochure) page = <BrochurePage code={brochure.code ?? ""} />;
  else if (!session || path === "/") page = null;
  // Keyed by the query: each search URL mounts a fresh page whose form state starts from the URL.
  else if (path === "/members") page = <SearchPage key={location.query.toString()} query={location.query} />;
  else if (edit) page = <EditPage memberId={edit.id ?? ""} />;
  else if (detail) page = <MemberPage memberId={detail.id ?? ""} query={location.query} />;
  else page = <NotFound />;

  return (
    <div class="app" onClick={onLinkClick}>
      <Header />
      <main id="main">
        <Toast />
        {page}
      </main>
      <footer class="app-footer">Northwind Health is a fictitious company. All data is synthetic.</footer>
    </div>
  );
}

const root = document.getElementById("app");
if (root) render(<App />, root);
