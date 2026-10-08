import uuid
from datetime import date, datetime

import anyio
from fastapi import APIRouter
from pydantic import model_validator

from app.common.constants import DOWNLOAD_URL_TTL_SECONDS, EXPORT_MAX_DAYS
from app.common.enums import ExportStatus, JobType
from app.common.schemas import ERROR_RESPONSES, Schema
from app.core import aws
from app.core.config import get_settings
from app.core.deps import ManagerActor, StaffActor, Uow
from app.jobs.queue import enqueue
from app.modules.reports.models import Export
from app.modules.reports.service import DashboardQueries, ExportRepository

router = APIRouter(prefix="/reports", tags=["reports"], responses=ERROR_RESPONSES)


class VolumePoint(Schema):
    day: date
    count: int


class AgentLoad(Schema):
    user_id: uuid.UUID
    full_name: str
    open: int


class Dashboard(Schema):
    open_by_status: dict[str, int]
    open_total: int
    breached_open: int
    first_response_p50_minutes: float | None
    first_response_p90_minutes: float | None
    sla_attainment_percent: float | None
    volume: list[VolumePoint]
    agent_load: list[AgentLoad]
    window_days: int


class ExportIn(Schema):
    from_date: date
    to_date: date

    @model_validator(mode="after")
    def valid_range(self) -> "ExportIn":
        if self.to_date < self.from_date or (self.to_date - self.from_date).days > EXPORT_MAX_DAYS:
            raise ValueError(f"Pick a range of at most {EXPORT_MAX_DAYS} days, end after start.")
        return self


class ExportOut(Schema):
    id: uuid.UUID
    status: ExportStatus
    from_date: date
    to_date: date
    row_count: int | None
    created_at: datetime
    download_url: str | None = None


@router.get("/dashboard", response_model=Dashboard)
async def dashboard(actor: StaffActor, uow: Uow) -> Dashboard:
    return Dashboard.model_validate(await DashboardQueries(uow.session, actor.org_id).summary())


@router.post("/exports", response_model=ExportOut, status_code=202)
async def start_export(body: ExportIn, actor: ManagerActor, uow: Uow) -> ExportOut:
    """Runs in the worker; the console is told over WebSocket when it is ready."""
    export = ExportRepository(uow.session, actor.org_id).add(
        Export(requested_by=actor.user_id, from_date=body.from_date, to_date=body.to_date)
    )
    await uow.session.flush()
    export_id, org_id = export.id, actor.org_id

    async def queue_job() -> None:
        await enqueue(JobType.EXPORT_CSV, {"org_id": org_id, "export_id": export_id}, f"export:{export_id}")

    uow.after_commit(queue_job)
    await uow.commit()
    return ExportOut.model_validate(export)


@router.get("/exports/{export_id}", response_model=ExportOut)
async def get_export(export_id: uuid.UUID, actor: ManagerActor, uow: Uow) -> ExportOut:
    export = await ExportRepository(uow.session, actor.org_id).get(export_id)
    out = ExportOut.model_validate(export)
    if export.status == ExportStatus.READY and export.s3_key:
        params = {"Bucket": get_settings().files_bucket, "Key": export.s3_key}
        out.download_url = await anyio.to_thread.run_sync(
            lambda: aws.s3_public().generate_presigned_url("get_object", Params=params, ExpiresIn=DOWNLOAD_URL_TTL_SECONDS)
        )
    return out
