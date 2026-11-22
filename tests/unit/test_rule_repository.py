from pathlib import Path

import pytest

from fafsa_edit_rule_processor.rules.repository import (
    RuleConfigError,
    YamlRuleConfigRepository,
)

SHIPPED_RULES = Path(__file__).parents[2] / "config" / "rules.yaml"

REQUIRED_RULE_IDS = {
    "STUDENT_MIN_AGE",
    "SSN_FORMAT",
    "DEPENDENT_PARENT_INCOME",
    "NON_NEGATIVE_INCOME",
    "COLLEGE_WITHIN_HOUSEHOLD",
    "STATE_CODE",
    "MARRIED_SPOUSE_INFO",
}


def test_shipped_rules_file_is_valid_and_complete() -> None:
    ruleset = YamlRuleConfigRepository(SHIPPED_RULES).load()

    assert ruleset.version
    assert {r.rule_id for r in ruleset.rules} == REQUIRED_RULE_IDS


def test_load_valid_file(tmp_path: Path) -> None:
    path = tmp_path / "rules.yaml"
    path.write_text(
        """
version: "test"
rules:
  - rule_id: R1
    severity: WARNING
    message: "msg"
    params: {threshold: 5}
"""
    )

    ruleset = YamlRuleConfigRepository(path).load()

    assert ruleset.version == "test"
    assert ruleset.rules[0].params == {"threshold": 5}


def test_missing_file_raises_rule_config_error(tmp_path: Path) -> None:
    with pytest.raises(RuleConfigError, match="failed to load rules"):
        YamlRuleConfigRepository(tmp_path / "nope.yaml").load()


@pytest.mark.parametrize(
    "content",
    [
        "version: [unclosed",  # malformed YAML
        "",  # empty file
        "version: v1\nrules:\n  - rule_id: R1\n    severity: BOGUS\n    message: m\n",
    ],
)
def test_invalid_content_raises_rule_config_error(tmp_path: Path, content: str) -> None:
    path = tmp_path / "rules.yaml"
    path.write_text(content)

    with pytest.raises(RuleConfigError):
        YamlRuleConfigRepository(path).load()
