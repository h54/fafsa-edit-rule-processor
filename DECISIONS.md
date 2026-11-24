
# Decisions

Philosophy: make it work, make it right

## Technology

- Python + FastAPI
- Bruno for versioned example API requests

## Time Spent

6-8 hours total. Sunday and Monday were travel days and I worked between flights, context switching added time.

## Validation

- collect all rule results; never stop at the first failure
- two layers:
  - **schema** (Pydantic): structure, types, always-required fields (e.g. student DOB, SSN) → `422`
  - **rules**: value checks and conditional requirements → `200` with results
- schema is lenient on values (SSN is any string; parent income / spouse info optional) so rules can report problems with actionable messages
- schema normalizes: state codes trimmed + uppercased; income rounded to whole dollars (see Assumptions)
- rule outcomes: `PASSED`, `FAILED`, `SKIPPED` (doesn't apply), `ERRORED`
- status precedence: `INVALID` > `INCOMPLETE` (a rule errored) > `VALID_WITH_WARNINGS` > `VALID`
- a rule that raises is logged and reported as `ERRORED`; other rules still run. A buggy rule yields `INCOMPLETE`, never a 500 or a false `VALID`.

## Severity Levels

- `ERROR` → `INVALID`; `WARNING` → `VALID_WITH_WARNINGS`; `INFO` → no effect on status
- all 7 required rules are `ERROR` (each is unprocessable data). Severity is configurable.

## Rule Representation

- **logic in code, configuration in a store**
  - config: id, enabled, severity, message, params (e.g. `min_age: 14`)
  - logic: one small, tested function per rule, registered by id
- most mid-year changes are config (thresholds, severity, messages, disabling) → no code change
- new *kinds* of rules need code, intentionally: eligibility logic should be reviewed and tested
- config is checked against the registry at startup (unknown rule, missing param, bad placeholder → fail fast). Disabled rules without code are allowed (staging) but log a warning.
- adding a rule: function + YAML entry + tests (see README)
- rejected: a rules DSL in a database; it means building an interpreter and shipping untested logic

## Rule Order & Conflicts

- rules are independent pure functions, so currently order doesn't matter
- if rule dependencies are ever needed, make them explicit by rule id, not by order
- no conflicts by design: rules only flag problems, never approve or override, and each owns one concern (e.g. a missing spouse SSN is reported only by the marital status rule)

## Rule Storage

- loaded via a `RuleConfigRepository` interface; YAML implementation here (no external dependencies)
- production: Postgres implementation (audit history, admin edits)
- loaded into memory at startup, never per request
- changes apply on a service restart

## Consistency

- each request uses one immutable ruleset snapshot
- responses include the ruleset version, so results are traceable

## Performance & Concurrency

- rules are bound and messages formatted at startup; a request is one in-memory pass with no I/O
- scale with processes (`--workers N`, more containers)
- endpoint is synchronous (for now). FastAPI runs requests in a threadpool, so a slow rule blocks one thread and not the event loop
- go async when a rule needs I/O (internal service call, DB write)

## Production Considerations

- plain stdlib logging; productionization would mean structured logging
- no PII in logs or errors
- CI runs lint (ty, ruff, format check) and tests on every PR

## Testing

- rules: table-driven edge cases with a fixed `as_of` date
- engine: fake rules in an isolated registry
- end to end: both brief samples through the shipped `rules.yaml` and the API

## Assumptions

- valid states = 50 + DC; territories can be added in config
- spouse info = first name, last name, SSN; blank counts as missing
- income in whole dollars, as FAFSA collects it: parsed as `Decimal`, rounded IRS-style (half up). The rule judges the rounded amount, so −$0.01 to −$0.49 → $0 and passes.
- age is calculated as of the request date (server local)
