import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.common.enums import ErrorCode
from app.core.logging import log, logger, request_id_var

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Request id in, request id out, one access log line per request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if 0 < len(incoming) <= 64 else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Unhandled errors bypass FastAPI's handlers; answer with the envelope here,
            # while the request id is still known.
            logger.exception("unhandled error")
            response = JSONResponse(
                {
                    "error": {
                        "code": ErrorCode.INTERNAL_ERROR,
                        "message": "Something went wrong on our side.",
                        "details": None,
                        "request_id": request_id,
                    }
                },
                status_code=500,
            )
        finally:
            request_id_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        log(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            ms=round((time.perf_counter() - started) * 1000, 1),
            request_id=request_id,
        )
        return response
