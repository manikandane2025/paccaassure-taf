# paccaassure_taf.runner

The `pataf` CLI (Typer): run, report, history, gates, sinks, doctor, catalog, lint, config, ai, license.

**Status:** Phase 1 ships `pataf --version` and `pataf config show [--resolved]`. `run`, `doctor`, `lint` … arrive in Phase 2.

## Public API
- `cli.app` (Typer app), `cli.main()` (console script `pataf`).
- `python -m paccaassure_taf …` is identical — use it where endpoint security blocks `pataf.exe`.
- `pataf config show [--root DIR] [--env NAME] [--set KEY=VALUE]... [--resolved]`

## Layer
- May import: everything below it in both stacks (top of the runtime and post-run contracts).
- Enforced by import-linter (ARCHITECTURE §3). Never import upward.

## Invariants
- Thin: commands parse, call a package API, print. No business logic here.
- Wrap commands with `_handles_errors`: a `PatafError` prints what/cause/fix to stderr and exits with its `exit_code`.
- Exit codes per REPORTING §6 (config/framework errors = 2).
- License check only at entry points (run start, report build, sink publish).

## How to extend
- New command group: `x_app = typer.Typer(...)`; `app.add_typer(x_app, name="x")`; test with `typer.testing.CliRunner`.
- Document stable commands in the root `CLAUDE.md` command list.

## Read first
ARCHITECTURE.md §4, INTEGRATIONS.md, REPORTING.md §6 · root `CLAUDE.md` hard rules.
