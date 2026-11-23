import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from fafsa_edit_rule_processor.dependencies import get_engine
from fafsa_edit_rule_processor.models.application import FafsaApplication
from fafsa_edit_rule_processor.models.results import RuleOutcome, ValidationResult
from fafsa_edit_rule_processor.rules.engine import RuleEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/applications", tags=["applications"])


@router.post("/validate")
def validate_application(
    application: FafsaApplication,
    engine: Annotated[RuleEngine, Depends(get_engine)],
) -> ValidationResult:
    result = engine.validate(application)
    # Log outcomes only, never applicant data (PII).
    logger.info(
        "validated application: status=%s ruleset=%s failed=%s",
        result.status,
        result.ruleset_version,
        [r.rule_id for r in result.results if r.outcome is RuleOutcome.FAILED],
    )
    return result
