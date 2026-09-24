# ADR-0004 Desktop automation via Appium
Status: Proposed — confirm driver in Phase 5
Context: Many enterprise customers have Windows desktop clients. The reference repo has no desktop support.
Decision: Appium 2 server + Appium-Python-Client behind `paccaassure_taf.desktop`. Windows driver candidates: `appium-windows-driver` (depends on WinAppDriver, sparsely maintained) and `appium-novawindows-driver` (UIA-based, no WinAppDriver). Spike both against a representative customer desktop app, record the result here. Verify current maintenance status of both at spike time.
Consequences: Desktop suites need self-hosted Windows agents; they cannot run in Linux Docker. The element model is shared with web, so screen code looks like page code.
