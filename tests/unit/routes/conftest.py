from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fafsa_edit_rule_processor.config import Settings
from fafsa_edit_rule_processor.main import create_app


@pytest.fixture
def client(shipped_rules_path: Path) -> TestClient:
    return TestClient(create_app(Settings(rules_path=shipped_rules_path)))
