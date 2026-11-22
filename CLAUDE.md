# CLAUDE.md

## Workflow

- Make changes in small, reviewable steps. The user reviews every code change.
- Never run git actions (add, commit, branch, push, etc.) unless explicitly asked.
- Keep responses succinct and concise.

## Code

- Don't over-comment. Comment only non-obvious intent or decisions, never what the code plainly does.
- Use type annotations wherever possible (parameters, return types, variables where not inferable), including tests.
- No fluff tests. Every test must verify meaningful behavior; skip trivial getters, framework behavior, and redundant variations.

## Project

- Python 3.14, FastAPI, Pydantic, managed with `uv`.
- `make test` — unit tests with coverage (`tests/unit`)
- `make lint` — ty + ruff
- `make format` — ruff format
- `make run` — run the service locally on port 8000
- Rule logic lives in code; rule configuration (severity, message, params, enabled) lives in `config/rules.yaml`. See DECISIONS.md.
