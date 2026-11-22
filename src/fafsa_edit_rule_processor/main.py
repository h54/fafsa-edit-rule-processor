from fastapi import FastAPI
from starlette.responses import RedirectResponse

from fafsa_edit_rule_processor.routes import core


def create_app() -> FastAPI:
    app = FastAPI(
        title="FAFSA Edit Rule Processor",
        description="Applies validations to applicant FAFSA data",
        contact={"email": "chris.declama@protonmail.com"},
        version="1.0",
    )

    @app.get("/", include_in_schema=False)
    def redirect_to_root():
        return RedirectResponse(url="/docs")
        ...

    # routes
    app.include_router(core.router)

    return app
