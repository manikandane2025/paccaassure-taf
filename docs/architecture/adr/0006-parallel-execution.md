# ADR-0006 Parallel execution
Status: Proposed — decide in Phase 8
Options: (a) behavex; (b) PaccaAssureTAF-native sharder: `pataf run --workers N` splits by feature (or scenario for `@parallel-scenario`), runs Behave subprocesses, merges result events into one run; (c) CI matrix sharding `--shard i/N`.
Leaning: (b)+(c) for full control of hooks, evidence, and merged results; benchmark behavex before deciding (note: behavex brings its own reporting, which would have to be bypassed in favour of PaccaAssureTAF result events).
