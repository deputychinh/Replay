"""SQS worker: receive → claim idempotency key → run handler in one transaction → delete.

A failing job is not deleted: SQS makes it visible again and, after 5 tries,
moves it to the dead-letter queue (alarm in CloudWatch).

  python -m app.worker               # in AWS (EventBridge sends the schedules)
  python -m app.worker --schedule    # locally: also enqueue SLA scan / auto-close on a timer
"""

import asyncio
import contextlib
import json
import signal
import sys
import time
from typing import Any

import anyio

from app.common.constants import (
    AUTO_CLOSE_INTERVAL_SECONDS,
    QUEUE_BATCH_SIZE,
    QUEUE_WAIT_SECONDS,
    SLA_SCAN_INTERVAL_SECONDS,
)
from app.common.enums import JobType
from app.core import aws
from app.core.config import get_settings
from app.core.logging import log, logger, setup_logging
from app.db.session import SessionFactory
from app.db.unit_of_work import UnitOfWork
from app.jobs.idempotency import claim
from app.jobs.queue import enqueue
from app.jobs.registry import handlers

HANDLERS = handlers()


async def process(body: str) -> None:
    job = json.loads(body)
    job_type, key = JobType(job["type"]), job["key"]
    started = time.perf_counter()
    async with SessionFactory() as session:
        uow = UnitOfWork(session)
        # Scans run every minute by design; their key is per-minute, so only duplicates are skipped.
        if not await claim(session, key):
            log("job skipped (already processed)", job=job_type, key=key)
            return
        await HANDLERS[job_type](job["payload"], uow)
        await uow.commit()
    log("job done", job=job_type, key=key, ms=round((time.perf_counter() - started) * 1000, 1))


async def receive() -> list[dict[str, Any]]:
    response = await anyio.to_thread.run_sync(
        lambda: aws.sqs().receive_message(
            QueueUrl=get_settings().queue_url, MaxNumberOfMessages=QUEUE_BATCH_SIZE, WaitTimeSeconds=QUEUE_WAIT_SECONDS
        )
    )
    return list(response.get("Messages", []))


async def delete(receipt: str) -> None:
    await anyio.to_thread.run_sync(lambda: aws.sqs().delete_message(QueueUrl=get_settings().queue_url, ReceiptHandle=receipt))


async def consume(stop: asyncio.Event) -> None:
    while not stop.is_set():
        for message in await receive():
            try:
                await process(message["Body"])
                await delete(message["ReceiptHandle"])
            except Exception:
                logger.exception("job failed; SQS will retry it")


async def schedule(stop: asyncio.Event) -> None:
    """Local stand-in for the EventBridge rules in infra/cdk."""
    last_close = 0.0
    while not stop.is_set():
        now = time.time()
        minute = int(now // SLA_SCAN_INTERVAL_SECONDS)
        await enqueue(JobType.SLA_SCAN, {}, f"sla-scan:{minute}")
        if now - last_close >= AUTO_CLOSE_INTERVAL_SECONDS:
            await enqueue(JobType.AUTO_CLOSE, {}, f"auto-close:{int(now // AUTO_CLOSE_INTERVAL_SECONDS)}")
            last_close = now
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=SLA_SCAN_INTERVAL_SECONDS)


async def main(with_schedule: bool) -> None:
    setup_logging()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    log("worker started", schedule=with_schedule)
    tasks = [consume(stop)] + ([schedule(stop)] if with_schedule else [])
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main("--schedule" in sys.argv))
