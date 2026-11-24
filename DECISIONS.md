
# Decisions

Philosophy: make it work, make it right

## Technology

- Python + FastAPI - if I had more time, I would've used Java
- Bruno

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
- all 7 required rules are `ERROR` (each is unprocessable data). Severity is configurable, so a rule can be downgraded mid-year without a deploy.

## Rule Representation

- **logic in code, configuration in a store**
  - config: id, enabled, severity, message, params (e.g. `min_age: 14`)
  - logic: one small, tested function per rule, registered by id
- most mid-year changes are config (thresholds, severity, messages, disabling) → no deploy
- new *kinds* of rules need code, intentionally: eligibility logic should be reviewed and tested
- rejected: a rules DSL in a database. Flexible, but means building an interpreter and shipping untested logic.
- config is checked against the registry at startup (unknown rule, missing param, bad placeholder → fail fast). Disabled rules without code are allowed (staging) but log a warning.
- adding a rule: function + YAML entry + tests (see README)

## Rule Order & Conflicts

- rules are independent pure functions, so order doesn't matter; results return in config order
- conflicts avoided by design: each rule owns one concern (e.g. missing spouse SSN is reported only by the marital status rule), and rules only flag problems, never approve or override
- if rule dependencies are ever needed, make them explicit by rule id, not by order

## Rule Storage

- loaded via a `RuleConfigRepository` interface; YAML implementation here (no external dependencies)
- production: Postgres implementation for audit history and admin edits
- loaded into memory at startup, never per request
- changes apply on restart. Future: hot reload that validates the new config and atomically swaps the engine, keeping the old one on failure.

## Consistency

- each request uses one immutable ruleset snapshot
- responses include the ruleset version, so results are traceable
- future: effective dates / award year on rules

## Performance & Concurrency

- rules are bound and messages formatted at startup; a request is one in-memory pass with no I/O
- scale with processes (`--workers N`, more containers), not async: the work is CPU-bound
- endpoint is sync on purpose: nothing to `await`, and FastAPI runs it in a threadpool, so a slow rule blocks one thread rather than the event loop
- go async when a rule needs I/O (internal service call, DB write): async clients, concurrent I/O rules with timeouts; a failed dependency reports `ERRORED`, never a false `VALID`
- bulk: a batch endpoint, or run `RuleEngine` in a queue worker (it has no HTTP dependency)

## Production Considerations

- plain stdlib logging; production would use JSON logs + request IDs
- no PII in logs or errors: logs record status, ruleset version, failed rule ids; 422s omit Pydantic's `input` echo
- CI runs lint (ty, ruff, format check) and tests on every PR

## Testing

- rules: table-driven edge cases (birthday boundary, non-ASCII digits, zero income, blank fields) with a fixed `as_of` date
- engine: fake rules in an isolated registry
- end to end: both brief samples through the shipped `rules.yaml` and the API
- the shipped `rules.yaml` is tested, so a bad config fails CI, not startup

## Assumptions

- valid states = 50 + DC; territories can be added in config
- spouse info = first name, last name, SSN; blank counts as missing
- income in whole dollars, as FAFSA collects it: parsed as `Decimal`, rounded IRS-style (half up, not banker's). The rule judges the rounded amount, so −$0.01 to −$0.49 → $0 and passes.
- negative income is `ERROR` per the brief, though real AGI can be negative; arguably a `WARNING`
- age is calculated as of the request date (server local)

## Time Spent

- TODO
