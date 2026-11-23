from pathlib import Path
from typing import Protocol

import yaml
from pydantic import ValidationError

from fafsa_edit_rule_processor.rules.config import RuleConfigError, RuleSet


class RuleConfigRepository(Protocol):
    """Source of rule configuration.

    The file-backed implementation below keeps the service dependency-free; in
    production a database-backed implementation would provide change history and
    admin edits without a deployment.
    """

    def load(self) -> RuleSet: ...


class YamlRuleConfigRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> RuleSet:
        try:
            with self._path.open() as f:
                data = yaml.safe_load(f)
            return RuleSet.model_validate(data)
        except (OSError, yaml.YAMLError, ValidationError) as e:
            raise RuleConfigError(f"failed to load rules from {self._path}: {e}") from e
