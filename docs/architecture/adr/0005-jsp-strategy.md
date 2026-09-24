# ADR-0005 Legacy JSP/Servlet automation
Status: Accepted (IE-mode sub-decision Proposed)
Decision: JSP UIs are driven by Playwright through `paccaassure_taf.jsp`, adding: frameset/iframe-aware locators, full-page postback waits, session (JSESSIONID) handling, popup windows, generated-id handling, and a `ServletClient` for direct HTTP form posts with token extraction (Struts/CSRF) for fast data setup and servlet-level checks.
Open question: if any legacy app only works in IE mode, Playwright cannot drive it. Fallback: optional `paccaassure-taf-jsp-iemode` plugin (Selenium + IEDriver on Windows agents). Build only if confirmed.
