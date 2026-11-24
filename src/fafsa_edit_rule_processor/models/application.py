"""FAFSA application request schema.

Validates structure, types, and the presence of fields every application must
have. Values are loosely typed (e.g. SSN is any string) and conditionally
required fields are optional, so edit rules, not the schema, report those
problems with an actionable message.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel


def _round_to_dollar(value: Any) -> Any:
    """Round to whole dollars, IRS-style (half up: $0.50 and above rounds up).

    Non-numeric input is passed through unchanged for the int validator to reject.
    """
    try:
        return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    except InvalidOperation, ValueError:
        return value


StateCode = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True)]
WholeDollars = Annotated[int, BeforeValidator(_round_to_dollar)]


class FafsaServiceSchema(BaseModel):
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


class StudentInfo(FafsaServiceSchema):
    first_name: str
    last_name: str
    ssn: str
    date_of_birth: date


class SpouseInfo(FafsaServiceSchema):
    first_name: str | None = None
    last_name: str | None = None
    ssn: str | None = None


class Household(FafsaServiceSchema):
    number_in_household: int
    number_in_college: int


class Income(FafsaServiceSchema):
    student_income: WholeDollars
    parent_income: WholeDollars | None = None


class FafsaApplication(FafsaServiceSchema):
    student_info: StudentInfo
    dependency_status: DependencyStatus
    marital_status: MaritalStatus
    spouse_info: SpouseInfo | None = None
    household: Household
    income: Income
    state_of_residence: StateCode
