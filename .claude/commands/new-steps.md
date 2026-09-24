Add BDD steps for: $ARGUMENTS

1. Search `docs/catalog/steps.md` for existing patterns with the same meaning. Reuse wins; report reuse candidates before writing anything new.
2. Follow step vocabulary in `docs/conventions/CODING_STANDARDS.md` (no UI words, roles as `UserRole`).
3. Implement with `paccaassure_taf.bdd` typed decorators; each body is ONE call to a flow/page/expect. Parameters typed by annotation.
4. If logic is needed, add it to a Flow, not the step.
5. Tag the feature per taxonomy, including `@tms:` and `@req:`.
6. Run `uv run pataf run --dry-run` and `uv run pataf lint steps`, then the scenario itself.
