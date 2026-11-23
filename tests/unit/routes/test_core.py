from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fafsa_edit_rule_processor.config import Settings
from fafsa_edit_rule_processor.main import create_app
from fafsa_edit_rule_processor.rules.config import RuleConfigError


def test_healthz_returns_ok(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_propertiez_reports_active_ruleset(client: TestClient) -> None:
    body = client.get("/propertiez").json()

    assert body["ruleset"]["version"] == "2026-27.1"
    assert len(body["ruleset"]["rules"]) == 7
    assert body["settings"]["log_level"] == "INFO"


def test_app_fails_to_start_with_invalid_rules(tmp_path: Path) -> None:
    rules = tmp_path / "rules.yaml"
    rules.write_text(
        "version: v1\nrules:\n  - rule_id: NOT_IMPLEMENTED\n"
        "    severity: ERROR\n    message: m\n"
    )

    with pytest.raises(RuleConfigError):
        create_app(Settings(rules_path=rules))
