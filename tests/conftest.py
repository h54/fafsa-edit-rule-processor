import json
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
def shipped_rules_path() -> Path:
    return PROJECT_ROOT / "config" / "rules.yaml"


@pytest.fixture
def valid_application_data() -> dict[str, Any]:
    return _load_json("valid_application.json")


@pytest.fixture
def invalid_application_data() -> dict[str, Any]:
    return _load_json("invalid_application.json")
