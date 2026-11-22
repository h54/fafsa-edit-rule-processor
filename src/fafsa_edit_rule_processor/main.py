import logging

from fastapi import FastAPI
from starlette.responses import RedirectResponse

from fafsa_edit_rule_processor.config import Settings
from fafsa_edit_rule_processor.routes import core


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = FastAPI(
        title="FAFSA Edit Rule Processor",
        description="Applies validations to applicant FAFSA data",
        contact={"email": "chris.declama@protonmail.com"},
        version="1.0",
    )
    app.state.settings = settings

    @app.get("/", include_in_schema=False)
    def redirect_to_docs():
        return RedirectResponse(url="/docs")

    # routes
    app.include_router(core.router)

    return app
