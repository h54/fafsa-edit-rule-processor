
# FAFSA Edit Rule Processor

## What is this?

The `fafsa-edit-rule-processor` is a REST service that accepts [FAFSA](https://studentaid.gov/h/apply-for-aid/fafsa) data and applies a series of validation rules ("edits") to determine applicant validity. All rules are applied to every application, and the response reports each rule's outcome, what's wrong, and which fields to fix.

Design decisions and trade-offs are in [DECISIONS.md](DECISIONS.md).

## Configuration

### Dependencies

- python 3.14
- uv
- make

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `FAFSA_RULES_PATH` | `config/rules.yaml` | Rule configuration file |
| `FAFSA_LOG_LEVEL` | `INFO` | Log level |

### Rules

Rule configuration lives in [`config/rules.yaml`](config/rules.yaml). Each rule's severity (`ERROR`, `WARNING`, `INFO`), message, params, and `enabled` flag can be changed without a code change; bump `version` with every change. Changes take effect on restart. An invalid file (unknown rule, missing param, bad severity) stops the service from starting.

## Running

```sh
make sync   # create the virtual environment
make run    # http://localhost:8000 (redirects to the OpenAPI docs)
```

## Testing

```sh
make test    # unit tests with coverage
make lint    # ty + ruff
make format  # ruff format
```

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/applications/validate` | Validate an application |
| `GET` | `/healthz` | Health check |
| `GET` | `/propertiez` | Active settings and ruleset |
| `GET` | `/docs` | OpenAPI docs |

### Example

```sh
curl -s -X POST http://localhost:8000/v1/applications/validate \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/invalid_application.json
```

A structurally valid application returns `200`, even when rules fail (results abbreviated):

```json
{
  "status": "INVALID",
  "rulesetVersion": "2026-27.1",
  "summary": { "total": 7, "passed": 0, "failed": 7, "skipped": 0, "errored": 0 },
  "results": [
    {
      "ruleId": "SSN_FORMAT",
      "outcome": "FAILED",
      "severity": "ERROR",
      "message": "SSN must be exactly 9 digits, with no dashes or spaces.",
      "fields": ["studentInfo.ssn"]
    },
    {
      "ruleId": "COLLEGE_WITHIN_HOUSEHOLD",
      "outcome": "FAILED",
      "severity": "ERROR",
      "message": "Number in college cannot exceed number in household.",
      "fields": ["household.numberInCollege", "household.numberInHousehold"]
    }
  ]
}
```

- `status`: `VALID`, `VALID_WITH_WARNINGS`, `INCOMPLETE` (a rule errored), or `INVALID`
- `outcome`: `PASSED`, `FAILED`, `SKIPPED` (rule doesn't apply, e.g. spouse rule for a single student), or `ERRORED`
- `fields`: JSON paths of the input fields to correct

A malformed application (missing required field, wrong type, unknown field) returns `422` with the offending field's location.

### How a request flows

```mermaid
sequenceDiagram
    participant C as Client
    participant API as POST /v1/applications/validate
    participant S as FafsaApplication (schema)
    participant E as RuleEngine
    participant R as Rules (rules/fafsa.py)

    Note over E: At startup: rules.yaml → RuleSet → RuleEngine<br/>(invalid config stops startup)
    C->>API: application JSON
    API->>S: validate structure & types
    alt malformed
        S-->>C: 422 + field locations
    else valid structure
        API->>E: validate(application)
        loop each enabled rule
            E->>R: evaluate(context)
            R-->>E: PASSED / FAILED / SKIPPED (or ERRORED if it raises)
        end
        E-->>API: ValidationResult (status, results, summary)
        API-->>C: 200 + ValidationResult
    end
```

## Adding a rule

1. Implement it in [`rules/fafsa.py`](src/fafsa_edit_rule_processor/rules/fafsa.py) and register it with an id (and any params it requires):
   ```python
   @registry.register("MAX_HOUSEHOLD", params=["max"])
   def max_household(ctx: RuleContext) -> Evaluation:
       if ctx.application.household.number_in_household > ctx.params["max"]:
           return Evaluation.failed("household.numberInHousehold")
       return Evaluation.passed()
   ```
2. Configure it in `config/rules.yaml`:
   ```yaml
   - rule_id: MAX_HOUSEHOLD
     severity: WARNING
     message: "Household size over {max}; please verify."
     params:
       max: 15
   ```
3. Add cases to [`tests/unit/rules/test_fafsa.py`](tests/unit/rules/test_fafsa.py).

## Project layout

```
config/rules.yaml              rule configuration
src/fafsa_edit_rule_processor/
├── main.py                    app factory; loads rules at startup
├── config.py                  settings (env vars)
├── models/
│   ├── application.py         request schema
│   └── results.py             response models
├── routes/
│   ├── applications.py        POST /v1/applications/validate
│   └── core.py                /healthz, /propertiez
└── rules/
    ├── config.py              RuleConfig / RuleSet
    ├── repository.py          RuleConfigRepository (YAML)
    ├── base.py                rule contract + registry
    ├── engine.py              RuleEngine
    └── fafsa.py               the FAFSA rules
tests/                         mirrors src/
```
