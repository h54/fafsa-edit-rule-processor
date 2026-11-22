from typing import Any

import pytest
from pydantic import ValidationError

from fafsa_edit_rule_processor.rules.models import RuleConfig, RuleSet


def _rule(rule_id: str = "R1", **overrides: Any) -> dict[str, Any]:
    return {"rule_id": rule_id, "severity": "ERROR", "message": "msg", **overrides}


@pytest.mark.parametrize(
    "overrides",
    [
        {"severity": "CRITICAL"},  # unknown severity
        {"message": ""},  # empty message
        {"rule_id": ""},  # empty id
        {"unexpected": True},  # typo'd / unknown key
    ],
)
def test_rule_config_rejects_invalid(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        RuleConfig.model_validate(_rule(**overrides))


def test_ruleset_rejects_duplicate_rule_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate rule_id"):
        RuleSet.model_validate({"version": "v1", "rules": [_rule("R1"), _rule("R1")]})


def test_ruleset_enabled_rules_excludes_disabled() -> None:
    ruleset = RuleSet.model_validate(
        {"version": "v1", "rules": [_rule("ON"), _rule("OFF", enabled=False)]}
    )

    assert [r.rule_id for r in ruleset.enabled_rules] == ["ON"]
