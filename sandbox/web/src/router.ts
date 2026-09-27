// Minimal history-API router (no dependency): real URLs, back/forward, deep links (nginx falls back to index.html).
import { useEffect, useState } from "preact/hooks";

const NAVIGATE_EVENT = "nwh:navigate";

export interface Location {
  path: string;
  query: URLSearchParams;
}

function current(): Location {
  return { path: window.location.pathname, query: new URLSearchParams(window.location.search) };
}

export function navigate(to: string, options: { replace?: boolean } = {}): void {
  if (options.replace) window.history.replaceState(null, "", to);
  else window.history.pushState(null, "", to);
  window.dispatchEvent(new Event(NAVIGATE_EVENT));
  window.scrollTo(0, 0);
}

export function useLocation(): Location {
  const [location, setLocation] = useState(current);
  useEffect(() => {
    const update = () => setLocation(current());
    window.addEventListener("popstate", update);
    window.addEventListener(NAVIGATE_EVENT, update);
    return () => {
      window.removeEventListener("popstate", update);
      window.removeEventListener(NAVIGATE_EVENT, update);
    };
  }, []);
  return location;
}

/** Intercept same-origin left clicks on <a href> so links navigate without a full page load. */
export function onLinkClick(event: MouseEvent): void {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }
  const anchor = (event.target as Element | null)?.closest("a");
  if (!anchor || anchor.target === "_blank" || anchor.hasAttribute("download")) return;
  const href = anchor.getAttribute("href");
  if (!href || !href.startsWith("/") || href.startsWith("//") || href.startsWith("/api/")) return;
  event.preventDefault();
  navigate(href);
}

/** Match "/members/:id/edit"-style patterns; returns params or null. */
export function match(pattern: string, path: string): Record<string, string> | null {
  const names: string[] = [];
  const regex = new RegExp(
    `^${pattern.replace(/:[a-z]+/g, (name) => {
      names.push(name.slice(1));
      return "([^/]+)";
    })}/?$`,
  );
  const found = regex.exec(path);
  if (!found) return null;
  return Object.fromEntries(names.map((name, index) => [name, decodeURIComponent(found[index + 1] ?? "")]));
}
