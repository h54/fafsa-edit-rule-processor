from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from fafsa_edit_rule_processor.models.application import FafsaApplication
from fafsa_edit_rule_processor.models.results import ApplicationStatus, RuleOutcome
from fafsa_edit_rule_processor.rules import fafsa
from fafsa_edit_rule_processor.rules.base import RuleContext, RuleFn
from fafsa_edit_rule_processor.rules.engine import RuleEngine
from fafsa_edit_rule_processor.rules.repository import YamlRuleConfigRepository
from tests.helpers import set_path

AS_OF = date(2026, 11, 23)
PARAMS = {"min_age": 14, "valid_codes": ["CA", "ME", "NY"]}
SPOUSE = {"firstName": "Sam", "lastName": "Grey", "ssn": "987654321"}

PASSED, FAILED, SKIPPED = RuleOutcome.PASSED, RuleOutcome.FAILED, RuleOutcome.SKIPPED

MakeContext = Callable[[dict[str, Any]], RuleContext]


@pytest.fixture
def make_context(valid_application_data: dict[str, Any]) -> MakeContext:
    def _make(overrides: dict[str, Any]) -> RuleContext:
        for path, value in overrides.items():
            set_path(valid_application_data, path, value)
        app = FafsaApplication.model_validate(valid_application_data)
        return RuleContext(app, PARAMS, AS_OF)

    return _make


CASES = [
    # STUDENT_MIN_AGE
    (fafsa.student_min_age, {"studentInfo.dateOfBirth": "2012-11-23"}, PASSED, ()),
    (
        fafsa.student_min_age,
        {"studentInfo.dateOfBirth": "2012-11-24"},  # turns 14 tomorrow
        FAILED,
        ("studentInfo.dateOfBirth",),
    ),
    # SSN_FORMAT
    (fafsa.ssn_format, {}, PASSED, ()),
    (fafsa.ssn_format, {"studentInfo.ssn": "12345678"}, FAILED, ("studentInfo.ssn",)),
    (
        fafsa.ssn_format,
        {"studentInfo.ssn": "123-45-6789"},
        FAILED,
        ("studentInfo.ssn",),
    ),
    (
        fafsa.ssn_format,
        {"studentInfo.ssn": "١٢٣٤٥٦٧٨٩"},  # non-ASCII digits
        FAILED,
        ("studentInfo.ssn",),
    ),
    (fafsa.ssn_format, {"studentInfo.ssn": ""}, FAILED, ("studentInfo.ssn",)),
    (
        fafsa.ssn_format,
        {"spouseInfo": SPOUSE | {"ssn": "bad"}},
        FAILED,
        ("spouseInfo.ssn",),
    ),
    (fafsa.ssn_format, {"spouseInfo": {"firstName": "Sam"}}, PASSED, ()),
    # DEPENDENT_PARENT_INCOME
    (
        fafsa.dependent_parent_income,
        {"income.parentIncome": ...},
        FAILED,
        ("income.parentIncome",),
    ),
    (fafsa.dependent_parent_income, {"income.parentIncome": 0}, PASSED, ()),
    (
        fafsa.dependent_parent_income,
        {"dependencyStatus": "independent", "income.parentIncome": ...},
        SKIPPED,
        (),
    ),
    # NON_NEGATIVE_INCOME
    (fafsa.non_negative_income, {"income.studentIncome": 0}, PASSED, ()),
    (fafsa.non_negative_income, {"income.parentIncome": ...}, PASSED, ()),
    (
        fafsa.non_negative_income,
        {"income.studentIncome": -1, "income.parentIncome": -0.50},
        FAILED,
        ("income.studentIncome", "income.parentIncome"),
    ),
    # COLLEGE_WITHIN_HOUSEHOLD
    (
        fafsa.college_within_household,
        {"household.numberInHousehold": 3, "household.numberInCollege": 3},
        PASSED,
        (),
    ),
    (
        fafsa.college_within_household,
        {"household.numberInHousehold": 2, "household.numberInCollege": 5},
        FAILED,
        ("household.numberInCollege", "household.numberInHousehold"),
    ),
    # STATE_CODE
    (fafsa.state_code, {"stateOfResidence": "NY"}, PASSED, ()),
    (fafsa.state_code, {"stateOfResidence": "XX"}, FAILED, ("stateOfResidence",)),
    # MARRIED_SPOUSE_INFO
    (fafsa.married_spouse_info, {}, SKIPPED, ()),
    (
        fafsa.married_spouse_info,
        {"maritalStatus": "married", "spouseInfo": SPOUSE},
        PASSED,
        (),
    ),
    (
        fafsa.married_spouse_info,
        {"maritalStatus": "married"},
        FAILED,
        ("spouseInfo.firstName", "spouseInfo.lastName", "spouseInfo.ssn"),
    ),
    (
        fafsa.married_spouse_info,
        {"maritalStatus": "married", "spouseInfo": SPOUSE | {"lastName": "  "}},
        FAILED,
        ("spouseInfo.lastName",),
    ),
]


@pytest.mark.parametrize(("rule", "overrides", "outcome", "fields"), CASES)
def test_rule(
    make_context: MakeContext,
    rule: RuleFn,
    overrides: dict[str, Any],
    outcome: RuleOutcome,
    fields: tuple[str, ...],
) -> None:
    evaluation = rule(make_context(overrides))

    assert evaluation.outcome is outcome
    assert evaluation.fields == fields


@pytest.fixture
def engine(shipped_rules_path: Path) -> RuleEngine:
    return RuleEngine(
        YamlRuleConfigRepository(shipped_rules_path).load(), fafsa.registry
    )


def test_valid_sample_passes_shipped_rules(
    engine: RuleEngine, valid_application_data: dict[str, Any]
) -> None:
    app = FafsaApplication.model_validate(valid_application_data)

    result = engine.validate(app, as_of=AS_OF)

    assert result.status is ApplicationStatus.VALID


def test_invalid_sample_fails_every_shipped_rule(
    engine: RuleEngine, invalid_application_data: dict[str, Any]
) -> None:
    app = FafsaApplication.model_validate(invalid_application_data)

    result = engine.validate(app, as_of=AS_OF)

    assert result.status is ApplicationStatus.INVALID
    assert {r.rule_id: r.outcome for r in result.results} == {
        "STUDENT_MIN_AGE": FAILED,
        "SSN_FORMAT": FAILED,
        "DEPENDENT_PARENT_INCOME": FAILED,
        "NON_NEGATIVE_INCOME": FAILED,
        "COLLEGE_WITHIN_HOUSEHOLD": FAILED,
        "STATE_CODE": FAILED,
        "MARRIED_SPOUSE_INFO": FAILED,
    }
