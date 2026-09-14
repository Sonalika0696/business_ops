"""Exception handlers producing the frozen error envelope (DESIGN.md §6):

    { "error": { "code": "string", "message": "string",
                 "field_errors": {"field": "message"} | null } }
"""

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Default `code` for HTTPExceptions raised with a plain string/None `detail`,
# keyed by status code. DESIGN.md §6 calls out "unauthorized" for 401
# explicitly; the rest follow the same snake_case convention.
_STATUS_CODE_DEFAULTS: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "validation_error",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_server_error",
}


def _envelope(code: str, message: str, field_errors: dict[str, str] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "field_errors": field_errors}}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle `HTTPException`.

    `exc.detail` may be:
      - a dict already shaped like `{"code": ..., "message": ..., "field_errors": ...}`
        (lets route handlers raise precise error codes), or
      - a plain string/None, in which case a default code is derived from the
        HTTP status code.
    """
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        body = _envelope(
            code=exc.detail["code"],
            message=exc.detail["message"],
            field_errors=exc.detail.get("field_errors"),
        )
    else:
        code = _STATUS_CODE_DEFAULTS.get(exc.status_code, "error")
        message = str(exc.detail) if exc.detail else code.replace("_", " ")
        body = _envelope(code=code, message=message)
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic/FastAPI request validation errors, mapping each error into `field_errors`."""
    field_errors: dict[str, str] = {}
    for err in exc.errors():
        # err["loc"] looks like ("body", "email") or ("query", "page_size")
        loc = [str(part) for part in err["loc"] if part not in ("body", "query", "path")]
        field = ".".join(loc) if loc else "__root__"
        field_errors[field] = err["msg"]
    body = _envelope(
        code="validation_error",
        message="Request validation failed.",
        field_errors=field_errors or None,
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=body)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort catch-all so an unexpected exception still returns the error envelope."""
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url)
    body = _envelope(code="internal_server_error", message="An unexpected error occurred.")
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Wire the error-envelope handlers onto a FastAPI app instance."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
