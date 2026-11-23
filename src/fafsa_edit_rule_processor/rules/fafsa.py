"""FAFSA edit rule implementations.

Each rule is registered under the rule_id used in config/rules.yaml. Field paths
in failures use the request's JSON (camelCase) names so clients can map them
back to their input.
"""

import re
from datetime import date

from fafsa_edit_rule_processor.models.application import (
    DependencyStatus,
    MaritalStatus,
)
from fafsa_edit_rule_processor.rules.base import Evaluation, RuleContext, RuleRegistry

registry = RuleRegistry()

# [0-9] rather than \d: \d also matches non-ASCII digits.
_SSN_PATTERN = re.compile(r"[0-9]{9}")


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _age_on(dob: date, as_of: date) -> int:
    had_birthday = (as_of.month, as_of.day) >= (dob.month, dob.day)
    return as_of.year - dob.year - (0 if had_birthday else 1)


@registry.register("STUDENT_MIN_AGE", params=["min_age"])
def student_min_age(ctx: RuleContext) -> Evaluation:
    dob = ctx.application.student_info.date_of_birth
    if _age_on(dob, ctx.as_of) < ctx.params["min_age"]:
        return Evaluation.failed("studentInfo.dateOfBirth")
    return Evaluation.passed()


@registry.register("SSN_FORMAT")
def ssn_format(ctx: RuleContext) -> Evaluation:
    app = ctx.application
    invalid = []
    if not _SSN_PATTERN.fullmatch(app.student_info.ssn):
        invalid.append("studentInfo.ssn")
    # A missing spouse SSN is MARRIED_SPOUSE_INFO's concern; only a provided one is checked here.
    spouse_ssn = app.spouse_info.ssn if app.spouse_info else None
    if spouse_ssn is not None and not _SSN_PATTERN.fullmatch(spouse_ssn):
        invalid.append("spouseInfo.ssn")
    return Evaluation.failed(*invalid) if invalid else Evaluation.passed()


@registry.register("DEPENDENT_PARENT_INCOME")
def dependent_parent_income(ctx: RuleContext) -> Evaluation:
    app = ctx.application
    if app.dependency_status is not DependencyStatus.DEPENDENT:
        return Evaluation.skipped()
    if app.income.parent_income is None:
        return Evaluation.failed("income.parentIncome")
    return Evaluation.passed()


@registry.register("NON_NEGATIVE_INCOME")
def non_negative_income(ctx: RuleContext) -> Evaluation:
    income = ctx.application.income
    negative = [
        path
        for path, amount in (
            ("income.studentIncome", income.student_income),
            ("income.parentIncome", income.parent_income),
        )
        if amount is not None and amount < 0
    ]
    return Evaluation.failed(*negative) if negative else Evaluation.passed()


@registry.register("COLLEGE_WITHIN_HOUSEHOLD")
def college_within_household(ctx: RuleContext) -> Evaluation:
    household = ctx.application.household
    if household.number_in_college > household.number_in_household:
        return Evaluation.failed(
            "household.numberInCollege", "household.numberInHousehold"
        )
    return Evaluation.passed()


@registry.register("STATE_CODE", params=["valid_codes"])
def state_code(ctx: RuleContext) -> Evaluation:
    if ctx.application.state_of_residence not in ctx.params["valid_codes"]:
        return Evaluation.failed("stateOfResidence")
    return Evaluation.passed()


@registry.register("MARRIED_SPOUSE_INFO")
def married_spouse_info(ctx: RuleContext) -> Evaluation:
    app = ctx.application
    if app.marital_status is not MaritalStatus.MARRIED:
        return Evaluation.skipped()
    spouse = app.spouse_info
    missing = [
        f"spouseInfo.{name}"
        for name, value in (
            ("firstName", spouse.first_name if spouse else None),
            ("lastName", spouse.last_name if spouse else None),
            ("ssn", spouse.ssn if spouse else None),
        )
        if _is_blank(value)
    ]
    return Evaluation.failed(*missing) if missing else Evaluation.passed()
