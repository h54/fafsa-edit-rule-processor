from collections import Counter
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Severity(StrEnum):
    ERROR = "ERROR"  # application cannot be processed until fixed
    WARNING = "WARNING"  # application can proceed but should be reviewed
    INFO = "INFO"  # informational only


class RuleConfig(BaseModel):
    """Configurable attributes of a single edit rule. The rule's logic lives in code."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str = Field(min_length=1)
    enabled: bool = True
    severity: Severity
    message: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class RuleSet(BaseModel):
    """A versioned, immutable snapshot of all rule configs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(min_length=1)
    rules: tuple[RuleConfig, ...]

    @model_validator(mode="after")
    def _rule_ids_are_unique(self) -> Self:
        counts = Counter(r.rule_id for r in self.rules)
        duplicates = [rule_id for rule_id, n in counts.items() if n > 1]
        if duplicates:
            raise ValueError(f"duplicate rule_id(s): {sorted(duplicates)}")
        return self

    @property
    def enabled_rules(self) -> tuple[RuleConfig, ...]:
        return tuple(r for r in self.rules if r.enabled)
