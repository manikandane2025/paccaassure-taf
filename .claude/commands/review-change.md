Review a change (read-only): $ARGUMENTS

1. Read-only: do not edit files, run formatters with `--fix`, commit, or push. Only read and run checks.
2. Determine scope: the diff for $ARGUMENTS (a branch, commit range, or "working tree"). Read CLAUDE.md hard rules and the spec/ADR for each touched area.
3. Run `uv run python scripts/dev.py check` and note any failures.
4. Check each hard rule against the diff: customer neutrality, typing (no `Any`, no raw strings where enums exist), layer contracts, one-line steps, no sleeps, no secrets/sensitive data, reuse before create, result-schema contract, docstrings with examples, "ships complete" (tests, docs, CHANGELOG), SemVer.
5. Output exactly this structure (JSON, then a 3-line human summary):
   ```json
   {"status": "approve | needs_changes | reject",
    "findings": [{"rule": "<hard rule # or spec §>", "severity": "blocker | major | minor",
                  "file": "<path>", "line": 0, "description": "...", "fix_hint": "...", "confidence": 0.0}],
    "recommended_next_step": "fix findings | run e2e | update docs | merge"}
   ```
6. Never ask for or echo secrets; if the diff contains one, report it as a blocker and advise rotation.
