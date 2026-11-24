import logging
from collections import Counter
from dataclasses import dataclass
from datetime import date

from fafsa_edit_rule_processor.models.application import FafsaApplication
from fafsa_edit_rule_processor.models.results import (
    ApplicationStatus,
    ResultSummary,
    RuleOutcome,
    RuleResult,
    ValidationResult,
)
from fafsa_edit_rule_processor.rules.base import RuleContext, RuleRegistry, RuleSpec
from fafsa_edit_rule_processor.rules.config import (
    RuleConfig,
    RuleConfigError,
    RuleSet,
    Severity,
)

logger = logging.getLogger(__name__)

ERRORED_MESSAGE = (
    "This rule could not be evaluated; the application was not fully validated."
)


@dataclass(frozen=True)
class _BoundRule:
    config: RuleConfig
    spec: RuleSpec
    message: str


class RuleEngine:
    """Applies every enabled rule in a ruleset to an application.

    Config is checked against the registry at construction, so a bad ruleset
    fails at startup rather than on a request. Rules are independent of each
    other, so evaluation order does not affect the result; results are returned
    in config order.
    """

    def __init__(self, ruleset: RuleSet, registry: RuleRegistry) -> None:
        self.ruleset = ruleset
        self._rules = tuple(_bind(c, registry) for c in ruleset.enabled_rules)
        for config in ruleset.rules:
            if not config.enabled and registry.get(config.rule_id) is None:
                logger.warning(
                    "disabled rule %r has no implementation; it will fail to load "
                    "if enabled",
                    config.rule_id,
                )

    def validate(
        self, application: FafsaApplication, as_of: date | None = None
    ) -> ValidationResult:
        as_of = as_of or date.today()
        results = tuple(_evaluate(rule, application, as_of) for rule in self._rules)
        return ValidationResult(
            status=_status(results),
            ruleset_version=self.ruleset.version,
            summary=_summary(results),
            results=results,
        )


def _bind(config: RuleConfig, registry: RuleRegistry) -> _BoundRule:
    spec = registry.get(config.rule_id)
    if spec is None:
        raise RuleConfigError(f"no implementation for rule {config.rule_id!r}")

    missing = spec.required_params - config.params.keys()
    if missing:
        raise RuleConfigError(
            f"rule {config.rule_id!r} is missing params: {sorted(missing)}"
        )

    try:
        message = config.message.format(**config.params)
    except (KeyError, IndexError, ValueError) as e:
        raise RuleConfigError(
            f"rule {config.rule_id!r} message has an invalid placeholder: {e}"
        ) from e

    return _BoundRule(config, spec, message)


def _evaluate(
    rule: _BoundRule, application: FafsaApplication, as_of: date
) -> RuleResult:
    try:
        evaluation = rule.spec.fn(RuleContext(application, rule.config.params, as_of))
    except Exception:
        logger.exception("rule %r raised during evaluation", rule.config.rule_id)
        return RuleResult(
            rule_id=rule.config.rule_id,
            outcome=RuleOutcome.ERRORED,
            severity=rule.config.severity,
            message=ERRORED_MESSAGE,
        )

    failed = evaluation.outcome is RuleOutcome.FAILED
    return RuleResult(
        rule_id=rule.config.rule_id,
        outcome=evaluation.outcome,
        severity=rule.config.severity,
        message=rule.message if failed else None,
        fields=evaluation.fields,
    )


def _status(results: tuple[RuleResult, ...]) -> ApplicationStatus:
    failed = {r.severity for r in results if r.outcome is RuleOutcome.FAILED}
    if Severity.ERROR in failed:
        return ApplicationStatus.INVALID
    if any(r.outcome is RuleOutcome.ERRORED for r in results):
        return ApplicationStatus.INCOMPLETE
    if Severity.WARNING in failed:
        return ApplicationStatus.VALID_WITH_WARNINGS
    return ApplicationStatus.VALID


def _summary(results: tuple[RuleResult, ...]) -> ResultSummary:
    counts = Counter(r.outcome for r in results)
    return ResultSummary(
        total=len(results),
        passed=counts[RuleOutcome.PASSED],
        failed=counts[RuleOutcome.FAILED],
        skipped=counts[RuleOutcome.SKIPPED],
        errored=counts[RuleOutcome.ERRORED],
    )
