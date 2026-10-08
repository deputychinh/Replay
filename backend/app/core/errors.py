"""AppError hierarchy and the single error envelope:
{ "error": { "code", "message", "details", "request_id" } }.
Services raise these; they never raise HTTPException.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.enums import ErrorCode
from app.core.logging import get_request_id, logger


class AppError(Exception):
    code = ErrorCode.INTERNAL_ERROR
    status = 500
    message = "Something went wrong on our side."

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details


class ValidationError(AppError):
    code, status, message = ErrorCode.VALIDATION_ERROR, 422, "Some fields are not valid."


class UnauthorizedError(AppError):
    code, status, message = ErrorCode.UNAUTHORIZED, 401, "Please sign in again."


class ForbiddenError(AppError):
    code, status, message = ErrorCode.FORBIDDEN, 403, "You do not have access to this."


class NotFoundError(AppError):
    code, status, message = ErrorCode.NOT_FOUND, 404, "We could not find that."


class ConflictError(AppError):
    code, status, message = ErrorCode.CONFLICT, 409, "This conflicts with the current state."


class InvalidTransitionError(AppError):
    code, status, message = ErrorCode.INVALID_TRANSITION, 409, "This status change is not allowed."


class RateLimitedError(AppError):
    code, status, message = ErrorCode.RATE_LIMITED, 429, "Too many requests. Please wait a moment."

    def __init__(self, retry_after: int) -> None:
        super().__init__(details={"retry_after_seconds": retry_after})
        self.retry_after = retry_after


def _body(code: ErrorCode, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details, "request_id": get_request_id()}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"Retry-After": str(exc.retry_after)} if isinstance(exc, RateLimitedError) else None
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(_body(ErrorCode.VALIDATION_ERROR, ValidationError.message, details), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.VALIDATION_ERROR
        return JSONResponse(_body(code, str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", exc_info=exc)
        return JSONResponse(_body(ErrorCode.INTERNAL_ERROR, AppError.message), status_code=500)
