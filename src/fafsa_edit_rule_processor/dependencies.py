from fastapi import Request

from fafsa_edit_rule_processor.config import Settings
from fafsa_edit_rule_processor.rules.engine import RuleEngine


def get_engine(request: Request) -> RuleEngine:
    return request.app.state.engine


def get_settings(request: Request) -> Settings:
    return request.app.state.settings
