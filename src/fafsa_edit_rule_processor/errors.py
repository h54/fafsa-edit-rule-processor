from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Ensure 422 is returned without the 'input' echo which could expose customer PII"""
    errors = [
        {"type": e["type"], "loc": e["loc"], "msg": e["msg"]} for e in exc.errors()
    ]

    return JSONResponse(status_code=422, content={"detail": errors})
