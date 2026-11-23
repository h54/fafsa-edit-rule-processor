from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, Self

from fafsa_edit_rule_processor.models.application import FafsaApplication
from fafsa_edit_rule_processor.models.results import RuleOutcome


@dataclass(frozen=True)
class RuleContext:
    application: FafsaApplication
    params: Mapping[str, Any]
    as_of: date  # "today", injectable so date-dependent rules are testable


@dataclass(frozen=True)
class Evaluation:
    outcome: RuleOutcome
    fields: tuple[str, ...] = ()

    @classmethod
    def passed(cls) -> Self:
        return cls(RuleOutcome.PASSED)

    @classmethod
    def skipped(cls) -> Self:
        return cls(RuleOutcome.SKIPPED)

    @classmethod
    def failed(cls, *fields: str) -> Self:
        return cls(RuleOutcome.FAILED, fields)


RuleFn = Callable[[RuleContext], Evaluation]


@dataclass(frozen=True)
class RuleSpec:
    fn: RuleFn
    required_params: frozenset[str]


class RuleRegistry:
    """Maps rule ids (as used in rule config) to their implementations."""

    def __init__(self) -> None:
        self._specs: dict[str, RuleSpec] = {}

    def register(
        self, rule_id: str, *, params: Iterable[str] = ()
    ) -> Callable[[RuleFn], RuleFn]:
        def decorator(fn: RuleFn) -> RuleFn:
            if rule_id in self._specs:
                raise ValueError(f"rule {rule_id!r} is already registered")
            self._specs[rule_id] = RuleSpec(fn, frozenset(params))
            return fn

        return decorator

    def get(self, rule_id: str) -> RuleSpec | None:
        return self._specs.get(rule_id)
