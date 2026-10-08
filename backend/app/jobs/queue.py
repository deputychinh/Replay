"""Send jobs to SQS. The worker (app/worker.py) runs them (DS-04)."""

import json
from typing import Any

import anyio

from app.common.enums import JobType
from app.core import aws
from app.core.config import get_settings


def job_body(job_type: JobType, payload: dict[str, Any], key: str) -> str:
    return json.dumps({"type": job_type, "payload": payload, "key": key}, default=str)


async def _send(body: str) -> None:
    await anyio.to_thread.run_sync(lambda: aws.sqs().send_message(QueueUrl=get_settings().queue_url, MessageBody=body))


async def enqueue(job_type: JobType, payload: dict[str, Any], key: str) -> None:
    """`key` makes the job idempotent: the worker skips a key it has already processed."""
    await _send(job_body(job_type, payload, key))
