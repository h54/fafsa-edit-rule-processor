from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from fafsa_edit_rule_processor.models.application import (
    DependencyStatus,
    FafsaApplication,
)
from tests.helpers import set_path


def test_parses_camel_case_sample(valid_application_data: dict[str, Any]) -> None:
    app = FafsaApplication.model_validate(valid_application_data)

    assert app.student_info.date_of_birth == date(2003, 5, 15)
    assert app.dependency_status is DependencyStatus.DEPENDENT
    assert app.income.parent_income == 65000
    assert app.spouse_info is None


def test_accepts_rule_violations_so_rules_can_report_them(
    invalid_application_data: dict[str, Any],
) -> None:
    app = FafsaApplication.model_validate(invalid_application_data)

    assert app.student_info.ssn == "invalid"
    assert app.income.parent_income is None
    assert app.household.number_in_college > app.household.number_in_household


def test_normalizes_state_code(valid_application_data: dict[str, Any]) -> None:
    data = set_path(valid_application_data, "stateOfResidence", " ny ")

    assert FafsaApplication.model_validate(data).state_of_residence == "NY"


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (5000.49, 5000),
        (5000.50, 5001),  # half up, not banker's rounding (which gives 5000)
        ("5000.50", 5001),
        (-0.49, 0),
        (-0.50, -1),
    ],
)
def test_rounds_income_to_whole_dollars_half_up(
    valid_application_data: dict[str, Any], amount: float | str, expected: int
) -> None:
    data = set_path(valid_application_data, "income.studentIncome", amount)

    assert FafsaApplication.model_validate(data).income.student_income == expected


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("dependencyStatus", "unknown"),
        ("maritalStatus", "divorced"),
        ("studentInfo.dateOfBirth", "not-a-date"),
        ("studentInfo.dateOfBirth", ...),
        ("studentInfo.ssn", ...),
        ("household.numberInCollege", "many"),
        ("income.studentIncome", "lots"),
        ("studentInfo.firstName", ...),
        ("household", ...),
        ("unexpectedField", True),
    ],
)
def test_rejects_malformed_structure(
    valid_application_data: dict[str, Any], path: str, value: Any
) -> None:
    with pytest.raises(ValidationError):
        FafsaApplication.model_validate(set_path(valid_application_data, path, value))
