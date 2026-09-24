# ADR-0003 Three-tier packaging and versioning
Status: Accepted
Decision: paccaassure-taf-core is distributed to customers as a wheel on their private index plus a runner image. App packs are customer wheels on the customer's feed, SemVer. Variant suites are not packages. Branching: main / develop / feature/* / release/* / hotfix/*. Consumers pin compatible ranges; Renovate/Dependabot opens upgrade PRs.
Consequences: No copy-paste reuse. Breaking changes need migration notes and a deprecation window.
