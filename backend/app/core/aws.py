"""boto3 clients. Locally they point at LocalStack; in AWS the endpoint is unset."""

from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config

from app.core.config import get_settings


def _client(service: str, endpoint: str | None) -> Any:
    settings = get_settings()
    extra: dict[str, Any] = {}
    if endpoint:
        extra = {"endpoint_url": endpoint, "aws_access_key_id": "test", "aws_secret_access_key": "test"}
    return boto3.client(service, region_name=settings.aws_region, config=Config(signature_version="s3v4"), **extra)  # type: ignore[call-overload]


@lru_cache
def sqs() -> Any:
    return _client("sqs", get_settings().aws_endpoint_url)


@lru_cache
def s3() -> Any:
    return _client("s3", get_settings().aws_endpoint_url)


@lru_cache
def s3_public() -> Any:
    """Signs URLs with the host the browser uses (LocalStack on localhost, real S3 in AWS)."""
    return _client("s3", get_settings().aws_public_endpoint_url)
