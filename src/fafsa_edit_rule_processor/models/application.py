"""FAFSA application request schema.

Validates structure and types only. Fields checked by an edit rule are optional
and loosely typed (e.g. SSN is any string) so the rule, not the schema, reports
the problem with an actionable message.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Schema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )


class DependencyStatus(StrEnum):
    DEPENDENT = "dependent"
    INDEPENDENT = "independent"


class MaritalStatus(StrEnum):
    SINGLE = "single"
    MARRIED = "married"


class StudentInfo(_Schema):
    first_name: str
    last_name: str
    ssn: str | None = None
    date_of_birth: date | None = None


class SpouseInfo(_Schema):
    first_name: str | None = None
    last_name: str | None = None
    ssn: str | None = None


class Household(_Schema):
    number_in_household: int
    number_in_college: int


class Income(_Schema):
    student_income: Decimal
    parent_income: Decimal | None = None


class FafsaApplication(_Schema):
    student_info: StudentInfo
    dependency_status: DependencyStatus
    marital_status: MaritalStatus
    spouse_info: SpouseInfo | None = None
    household: Household
    income: Income
    state_of_residence: str
