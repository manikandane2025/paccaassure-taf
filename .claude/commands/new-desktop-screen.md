Add a Windows desktop screen: $ARGUMENTS

1. Read `docs/specs/DRIVERS.md` (Desktop) and ADR-0004.
2. Inspect the app with Appium Inspector or `pataf desktop dump --window "<title>"` to get AutomationIds.
3. Create `<Noun>Screen(DesktopScreen)` with `window_title` and typed elements (AutomationId first).
4. Methods mirror web page conventions; navigation returns the next screen type.
5. Scenario tagged `@desktop`; runs only on Windows agents. Run type/lint checks locally.
