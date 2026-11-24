import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.responses import RedirectResponse

from fafsa_edit_rule_processor.config import Settings
from fafsa_edit_rule_processor.errors import validation_error_handler
from fafsa_edit_rule_processor.routes import applications_routes, core_routes
from fafsa_edit_rule_processor.rules import fafsa
from fafsa_edit_rule_processor.rules.engine import RuleEngine
from fafsa_edit_rule_processor.rules.repository import YamlRuleConfigRepository

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Fail fast: an invalid rules file stops startup rather than serving bad results.
    ruleset = YamlRuleConfigRepository(settings.rules_path).load()
    engine = RuleEngine(ruleset, fafsa.registry)
    logger.info(
        "loaded ruleset %s (%d of %d rules enabled)",
        ruleset.version,
        len(ruleset.enabled_rules),
        len(ruleset.rules),
    )

    app = FastAPI(
        title="FAFSA Edit Rule Processor",
        description="Applies validations to applicant FAFSA data",
        contact={"email": "chris.declama@protonmail.com"},
        version="1.0",
    )
    app.state.settings = settings
    app.state.engine = engine

    # custom handlers
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # ty: ignore[invalid-argument-type]

    @app.get("/", include_in_schema=False)
    def redirect_to_docs() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    # routes
    app.include_router(core_routes.router)
    app.include_router(applications_routes.router)

    return app
