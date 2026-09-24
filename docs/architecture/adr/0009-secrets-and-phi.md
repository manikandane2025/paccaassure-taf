# ADR-0009 Secrets and sensitive data
Status: Accepted
Decision: `SecretRef` URIs (`kv://vault/name`, `env://VAR`, `hcv://path#key`) resolved by `SecretProvider` plugins at first use; values are `SecretStr`. Model fields marked `Sensitive[...]` (PII/PHI/PCI) are masked in logs, result events, evidence, report, history and sink payloads. Masking happens at event-write time, so no downstream component ever sees raw values. CI runs gitleaks + a configurable sensitive-pattern set over repo, results and evidence.
