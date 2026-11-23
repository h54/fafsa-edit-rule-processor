from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from fafsa_edit_rule_processor.config import Settings
from fafsa_edit_rule_processor.dependencies import get_engine, get_settings
from fafsa_edit_rule_processor.rules.engine import RuleEngine

router = APIRouter(tags=["core"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/propertiez")
def propertiez(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[RuleEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Active configuration. Settings hold no secrets; allowlist fields if that changes."""
    return {
        "version": request.app.version,
        "settings": settings.model_dump(mode="json"),
        "ruleset": engine.ruleset.model_dump(mode="json"),
    }
