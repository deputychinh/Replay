"""CSV export job: stream rows from Postgres into a file, upload to S3, tell the requester."""

import csv
import io
import uuid
from datetime import UTC, datetime
from typing import Any

import anyio

from app.common.enums import EventName, ExportStatus
from app.core import aws
from app.core.config import get_settings
from app.db.unit_of_work import UnitOfWork
from app.modules.notifications.service import Notifier
from app.modules.reports.service import EXPORT_HEADER, ExportRepository, export_rows_query
from app.modules.users.repository import UserRepository

FETCH_ROWS = 1000


async def export_csv(payload: dict[str, Any], uow: UnitOfWork) -> None:
    org_id, export_id = uuid.UUID(payload["org_id"]), uuid.UUID(payload["export_id"])
    export = await ExportRepository(uow.session, org_id).get(export_id)
    export.status = ExportStatus.RUNNING

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_HEADER)
    count = 0
    result = await uow.session.stream(export_rows_query(org_id, export.from_date, export.to_date))
    async for partition in result.partitions(FETCH_ROWS):
        for row in partition:
            writer.writerow([v.isoformat() if isinstance(v, datetime) else v for v in row])
            count += 1

    key = f"exports/{org_id}/{export_id}.csv"  # exports/ expires after 7 days (S3 lifecycle)
    body = buffer.getvalue().encode()
    await anyio.to_thread.run_sync(
        lambda: aws.s3().put_object(Bucket=get_settings().files_bucket, Key=key, Body=body, ContentType="text/csv")
    )

    export.status, export.s3_key, export.row_count, export.finished_at = ExportStatus.READY, key, count, datetime.now(UTC)
    requester = await UserRepository(uow.session, org_id).find(export.requested_by)
    if requester:
        Notifier(uow, org_id).notify(requester, EventName.EXPORT_READY, f"Your export of {count} tickets is ready.")
