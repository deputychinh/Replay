"""Shapes shared by every module."""

import base64
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.common.enums import ErrorCode


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CursorPage[T](Schema):
    """Keyset pagination: pass next_cursor back as ?cursor= to get the next page."""

    items: list[T]
    next_cursor: str | None


class ApiErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    details: Any = None
    request_id: str | None = None


class ApiError(BaseModel):
    error: ApiErrorDetail


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {status: {"model": ApiError} for status in (401, 403, 404, 409, 422, 429)}


def encode_cursor(values: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(values, default=str).encode()).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    from app.core.errors import ValidationError

    try:
        return dict(json.loads(base64.urlsafe_b64decode(cursor.encode())))
    except (ValueError, TypeError) as exc:
        raise ValidationError("The cursor is not valid.") from exc


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)
