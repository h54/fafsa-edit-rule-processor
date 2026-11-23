from datetime import date
from typing import Any

import pytest

from fafsa_edit_rule_processor.models.application import FafsaApplication
from fafsa_edit_rule_processor.models.results import ApplicationStatus, RuleOutcome
from fafsa_edit_rule_processor.rules.base import Evaluation, RuleContext, RuleRegistry
from fafsa_edit_rule_processor.rules.config import RuleConfigError, RuleSet
from fafsa_edit_rule_processor.rules.engine import RuleEngine

registry = RuleRegistry()
registry.register("PASS")(lambda ctx: Evaluation.passed())
registry.register("FAIL")(lambda ctx: Evaluation.failed("a.b", "c"))
registry.register("FAIL_TOO")(lambda ctx: Evaluation.failed())
registry.register("SKIP")(lambda ctx: Evaluation.skipped())
registry.register("NEEDS_LIMIT", params=["limit"])(lambda ctx: Evaluation.passed())

seen_contexts: list[RuleContext] = []


@registry.register("BOOM")
def _boom(ctx: RuleContext) -> Evaluation:
    raise RuntimeError("bug in rule")


@registry.register("RECORD")
def _record(ctx: RuleContext) -> Evaluation:
    seen_contexts.append(ctx)
    return Evaluation.passed()


@pytest.fixture
def application(valid_application_data: dict[str, Any]) -> FafsaApplication:
    return FafsaApplication.model_validate(valid_application_data)


def _ruleset(*rules: dict[str, Any]) -> RuleSet:
    return RuleSet.model_validate({"version": "test-v1", "rules": rules})


def _rule(rule_id: str, severity: str = "ERROR", **overrides: Any) -> dict[str, Any]:
    return {"rule_id": rule_id, "severity": severity, "message": "msg"} | overrides


@pytest.mark.parametrize(
    ("rule", "error"),
    [
        (_rule("UNKNOWN"), "no implementation"),
        (_rule("NEEDS_LIMIT"), "missing params"),
        (_rule("PASS", message="over {limit}"), "invalid placeholder"),
    ],
)
def test_invalid_config_fails_at_construction(rule: dict[str, Any], error: str) -> None:
    with pytest.raises(RuleConfigError, match=error):
        RuleEngine(_ruleset(rule), registry)


def test_disabled_rules_are_not_bound_or_evaluated(
    application: FafsaApplication, caplog: pytest.LogCaptureFixture
) -> None:
    engine = RuleEngine(
        _ruleset(_rule("PASS"), _rule("UNKNOWN", enabled=False)), registry
    )

    result = engine.validate(application)

    assert [r.rule_id for r in result.results] == ["PASS"]
    assert "'UNKNOWN' has no implementation" in caplog.text


def test_erroring_rule_is_reported_and_others_still_run(
    application: FafsaApplication, caplog: pytest.LogCaptureFixture
) -> None:
    engine = RuleEngine(_ruleset(_rule("BOOM"), _rule("PASS")), registry)

    result = engine.validate(application)

    boom, passed = result.results
    assert boom.outcome is RuleOutcome.ERRORED
    assert boom.message
    assert passed.outcome is RuleOutcome.PASSED
    assert "bug in rule" in caplog.text


def test_summary_counts_outcomes(application: FafsaApplication) -> None:
    rules = [
        _rule("PASS"),
        _rule("FAIL"),
        _rule("FAIL_TOO"),
        _rule("SKIP"),
        _rule("BOOM"),
    ]

    result = RuleEngine(_ruleset(*rules), registry).validate(application)

    assert result.model_dump()["summary"] == {
        "total": 5,
        "passed": 1,
        "failed": 2,
        "skipped": 1,
        "errored": 1,
    }


def test_result_reports_each_rule_in_config_order(
    application: FafsaApplication,
) -> None:
    engine = RuleEngine(_ruleset(_rule("SKIP"), _rule("FAIL"), _rule("PASS")), registry)

    result = engine.validate(application)

    assert result.ruleset_version == "test-v1"
    assert [(r.rule_id, r.outcome) for r in result.results] == [
        ("SKIP", RuleOutcome.SKIPPED),
        ("FAIL", RuleOutcome.FAILED),
        ("PASS", RuleOutcome.PASSED),
    ]


def test_failed_rule_has_formatted_message_and_fields(
    application: FafsaApplication,
) -> None:
    rule = _rule("FAIL", message="must be under {limit}", params={"limit": 5})

    (result,) = RuleEngine(_ruleset(rule), registry).validate(application).results

    assert result.message == "must be under 5"
    assert result.fields == ("a.b", "c")


def test_passed_rule_has_no_message(application: FafsaApplication) -> None:
    (result,) = (
        RuleEngine(_ruleset(_rule("PASS")), registry).validate(application).results
    )

    assert result.message is None


def test_rule_receives_params_and_as_of(application: FafsaApplication) -> None:
    seen_contexts.clear()
    engine = RuleEngine(_ruleset(_rule("RECORD", params={"x": 1})), registry)

    engine.validate(application, as_of=date(2026, 1, 1))

    (ctx,) = seen_contexts
    assert ctx.params == {"x": 1}
    assert ctx.as_of == date(2026, 1, 1)
    assert ctx.application is application


@pytest.mark.parametrize(
    ("rules", "expected"),
    [
        ([_rule("PASS"), _rule("SKIP")], ApplicationStatus.VALID),
        ([_rule("PASS"), _rule("FAIL", "INFO")], ApplicationStatus.VALID),
        ([_rule("FAIL", "WARNING")], ApplicationStatus.VALID_WITH_WARNINGS),
        ([_rule("FAIL", "WARNING"), _rule("BOOM")], ApplicationStatus.INCOMPLETE),
        ([_rule("BOOM"), _rule("FAIL", "ERROR")], ApplicationStatus.INVALID),
        (
            [_rule("FAIL", "WARNING"), _rule("FAIL_TOO", "ERROR")],
            ApplicationStatus.INVALID,
        ),
    ],
)
def test_status_reflects_most_severe_outcome(
    application: FafsaApplication,
    rules: list[dict[str, Any]],
    expected: ApplicationStatus,
) -> None:
    result = RuleEngine(_ruleset(*rules), registry).validate(application)

    assert result.status is expected
