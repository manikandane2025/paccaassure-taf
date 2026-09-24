# PaccaAssureTAF — core

`paccaassure-taf-core` is the core package of **PaccaAssureTAF** (PaccaAssure Test Automation Framework): a commercial, customer-agnostic, AI-native test automation platform for modern web, legacy JSP, REST APIs, Windows desktop, databases and files — with its own reporting engine, history store and trend analytics.

> Status: **Phase 0 (skeleton)**. See [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md).

## Start here
- Humans and agents: [CLAUDE.md](CLAUDE.md) (mission, hard rules, commands, map of docs).
- Product principles: [docs/PRODUCT.md](docs/PRODUCT.md) · Architecture: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md).

## Developer setup (Windows, macOS, Linux)
Prerequisites: [uv](https://docs.astral.sh/uv/), Git, Docker (for the sandbox). PowerShell 7 is recommended on Windows but not required.

```text
uv sync --all-extras
uv run python -m pre_commit install
uv run python scripts/dev.py check
```

`scripts/dev.py --help` lists all dev tasks. CI runs exactly the same tasks (ADR-0014).

## License
Proprietary. See [LICENSE](LICENSE).
