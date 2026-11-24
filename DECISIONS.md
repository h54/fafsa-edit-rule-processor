
# Decisions

Philosophy: make it work, make it right

## Technology

- Python + FastAPI - if I had more time, I would've used Java
- Bruno

## Validation

- return full set of validations (pass/fail) instead of failing on the first
- two layers, kept separate:
  - **schema validation** (Pydantic): structure, types, and presence of fields every application must have (e.g. student date of birth and SSN). Malformed requests are rejected with `422`.
  - **edit rules**: value checks and conditional requirements. They run on any structurally valid application, even one with bad values, and return `200` with results.
- schema is deliberately lenient on values: conditionally required fields (e.g. `parentIncome` only if dependent, spouse info only if married) are optional, and values like SSN are plain strings, so the edit rules report these problems instead of a schema rejection
- state codes are normalized (trimmed, uppercased) in the schema, so `" ny "` is accepted as `NY`
- the SSN format rule applies to the spouse SSN too, when provided; a missing spouse SSN is reported only by the marital status rule, not twice
- each rule outcome is `PASSED`, `FAILED`, `SKIPPED` (rule not applicable, e.g. spouse rule for a single applicant), or `ERRORED`. Skipped is not reported as passed.
- overall status, by precedence: `INVALID` (an `ERROR` rule failed) > `INCOMPLETE` (a rule errored) > `VALID_WITH_WARNINGS` (a `WARNING` rule failed) > `VALID`. `INFO` failures don't affect status.
- a rule that raises is caught and logged, and reported as `ERRORED`; the other rules still run. One buggy rule degrades a result to `INCOMPLETE`, never to a 500 for every application, and never to a false `VALID`.
- a disabled rule with no implementation is allowed (so config can be staged before code ships) but logs a warning at startup

## Rule Representation

- **rule logic lives in code; rule configuration lives in a store**
  - config = id, enabled, severity, message, parameters (e.g. `min_age: 14`, list of valid state codes)
  - logic = a small, unit-tested class per rule type
- most mid-year changes are configuration changes (thresholds, severities, messages, disabling a rule). These need no deploy.
- adding a new *kind* of rule needs a code change. This is intentional: eligibility logic should go through code review and tests.
- considered and rejected: a rules DSL / expressions stored in a database. More flexible, but it means building and securing an interpreter, and untested rule logic can reach production.

## Rule Storage

- configuration is loaded through a `RuleConfigRepository` interface
- implemented here: a file-backed repository (YAML), so the service runs with no external dependencies
- in production: a Postgres-backed implementation of the same interface, which gives auditing, change history, and edits through an admin tool without a deploy. Not built here to keep the service easy to run within the time limit.
- rules are loaded into memory at startup, never read from the store per request
- config changes (enable/disable, severity, message, params) currently take effect on restart. Future: hot reload via an admin endpoint or periodic re-read that builds a new, validated `RuleEngine` and atomically swaps it in. An invalid config is rejected and the current engine keeps serving.

## Consistency

- each request is evaluated against one immutable ruleset snapshot, so a config reload during a request can't mix two rule versions
- the response includes the ruleset version, so every result can be traced to the exact rules that produced it
- future: effective dates / award year on rules

## Performance & Concurrency

- the validate endpoint is synchronous (`def`, not `async def`) on purpose: validation is pure CPU work against an in-memory ruleset (microseconds, no per-request I/O), so there is nothing to `await`
- FastAPI runs sync endpoints in a threadpool, so the event loop is never blocked. If a rule ever becomes slow or blocking, it ties up one thread rather than stalling every request, as it would in an `async def` endpoint.
- throughput for CPU-bound work scales with processes, not async: more uvicorn workers (`--workers N`) or more containers behind a load balancer
- **when to go async:** as soon as validation needs I/O, e.g. a rule that calls an internal service (identity/SSN verification) or a DB write (persisting results for audit). Then:
  - make the endpoint and rule evaluation `async`, using async clients (`asyncpg`, `httpx2`)
  - run I/O-bound rules concurrently (`asyncio.gather`) with per-call timeouts
  - a timed-out or failed dependency reports the rule as `ERRORED` (status `INCOMPLETE`), the same path as a buggy rule today, so an unavailable service never produces a false `VALID`

## Production Considerations

- logging is plain stdlib text; in production: JSON logs + request IDs for log aggregation and audit traceability
- PII is kept out of logs and error responses: validation logs record only status, ruleset version, and failed rule ids; 422 responses omit Pydantic's `input` echo so a rejected request never returns applicant data
