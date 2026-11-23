from collections import Counter
from enum import StrEnum

from pydantic import computed_field

from fafsa_edit_rule_processor.models.application import FafsaServiceSchema
from fafsa_edit_rule_processor.rules.config import Severity


class RuleOutcome(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"  # rule does not apply to this application
    ERRORED = "ERRORED"  # rule raised an exception; its result is unknown


class ApplicationStatus(StrEnum):
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    # a rule errored, so the application can't be called valid
    INCOMPLETE = "INCOMPLETE"
    INVALID = "INVALID"


class RuleResult(FafsaServiceSchema):
    rule_id: str
    outcome: RuleOutcome
    severity: Severity
    message: str | None = None  # set only when the rule failed or errored
    fields: tuple[str, ...] = ()  # JSON paths of the offending fields


class ResultSummary(FafsaServiceSchema):
    total: int
    passed: int
    failed: int
    skipped: int
    errored: int


class ValidationResult(FafsaServiceSchema):
    status: ApplicationStatus
    ruleset_version: str
    results: tuple[RuleResult, ...]

    @computed_field
    @property
    def summary(self) -> ResultSummary:
        counts = Counter(r.outcome for r in self.results)
        return ResultSummary(
            total=len(self.results),
            passed=counts[RuleOutcome.PASSED],
            failed=counts[RuleOutcome.FAILED],
            skipped=counts[RuleOutcome.SKIPPED],
            errored=counts[RuleOutcome.ERRORED],
        )
