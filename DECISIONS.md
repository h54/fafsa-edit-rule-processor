
# Decisions

## Technology

- Python + FastAPI - if I had more time, I would've used Java
- Bruno

## Validation

- return full set of validations (pass/fail) instead of failing on the first
- two layers, kept separate:
  - **schema validation** (Pydantic): structure and types only. Malformed requests are rejected with `422`.
  - **edit rules**: business logic. They run on any structurally valid application, even one with bad values, and return `200` with results.
- schema is deliberately lenient: fields that rules check (e.g. `parentIncome`, spouse info) are optional, and values like SSN are plain strings, so the edit rules report these problems instead of a schema rejection
- each rule outcome is `PASSED`, `FAILED`, or `SKIPPED` (rule not applicable, e.g. spouse rule for a single applicant). Skipped is not reported as passed.

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

## Consistency

- each request is evaluated against one immutable ruleset snapshot, so a config reload during a request can't mix two rule versions
- the response includes the ruleset version, so every result can be traced to the exact rules that produced it
- future: effective dates / award year on rules

## Production Considerations

- logging is plain stdlib text; in production: JSON logs + request IDs for log aggregation and audit traceability
