# ADR-0014 Tool-agnostic CI: tasks in Python, CI YAML as thin adapters
Status: Accepted
Context: PaccaAssureTAF must fit whatever CI a customer (and we) use: GitHub Actions, Azure Pipelines, Jenkins, GitLab. Logic embedded in one CI system's YAML is locked to that system, drifts between systems, and cannot be run locally. Shell one-liners also break across bash / PowerShell 5.1 / cmd (Windows is a first-class dev platform).
Decision:
1. Every quality check for core is a task in `scripts/dev.py` (typed, cross-shell Python, run as `uv run python scripts/dev.py <task>`): `lint`, `format-check`, `typecheck`, `imports`, `test`, `licenses`, `audit`, `check` (the aggregate), plus sandbox tasks. Developers, pre-commit and CI all run the same tasks.
2. CI definitions are thin adapters: install uv, `uv sync --frozen`, call `scripts/dev.py` tasks, publish artifacts/summaries natively. No test or lint logic lives in YAML.
3. Core's own CI starts on **GitHub Actions** (`.github/workflows/ci.yml`; the repo is hosted on GitHub). Azure Pipelines and Jenkins adapters for core are added later (Phase 8) and must call the same tasks.
4. The same principle governs customer-facing templates in `pipelines/` (Phase 8): they only call the `pataf` CLI.
Consequences: Adding a CI system is a small YAML file. Local runs reproduce CI exactly. `scripts/dev.py` is held to ruff + mypy like `src/` (but is not shipped in the wheel).
