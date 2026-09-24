Triage failing run/scenario: $ARGUMENTS

1. Read `results/<run-id>/run.json` (or `pataf report summary --run <id>`) and the test's evidence folder (masked logs, trace, screenshot, API exchanges).
2. Check history: `pataf history test <test_key> --last 20` and `pataf history signature <signature>` — has this failure signature been seen before? Is the test flaky or quarantined?
3. Classify: product defect / script defect / locator drift / environment / test data / flaky timing. Give evidence (step, element/endpoint, log lines, history).
4. Script/locator issue: propose a minimal fix; apply only if asked. Never add sleeps or blanket retries.
5. Product defect: draft a bug summary (no sensitive data) with steps, expected vs actual, signature id, evidence file names.
