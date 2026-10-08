"""Business flows B5 + B6: SLA scan (warn once, breach once), idempotent jobs, CSV export to S3."""

import json
import uuid
from datetime import UTC, date, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select, update

from app.common.enums import JobType, TicketEventType
from app.db.session import SessionFactory
from app.jobs.queue import job_body
from app.modules.notifications.models import Notification
from app.modules.tickets.models import Ticket, TicketEvent
from app.worker import process
from tests.integration.conftest import API, Jobs, body


async def _make_overdue(ticket_id: str) -> None:
    async with SessionFactory() as s:
        await s.execute(
            update(Ticket)
            .where(Ticket.id == uuid.UUID(ticket_id))
            .values(resolution_due_at=datetime.now(UTC) - timedelta(minutes=5))
        )
        await s.commit()


async def _count(ticket_id: str, event: TicketEventType) -> int:
    async with SessionFactory() as s:
        return int(
            await s.scalar(
                select(func.count())
                .select_from(TicketEvent)
                .where(TicketEvent.ticket_id == uuid.UUID(ticket_id), TicketEvent.type == event)
            )
            or 0
        )


async def test_sla_scan_flags_a_breach_exactly_once(
    client: AsyncClient, customer: dict[str, str], agent: dict[str, str], jobs: Jobs
) -> None:
    created = body(await client.post(f"{API}/tickets", headers=customer, json={"subject": "Slow export", "body": "x"}))
    await jobs.run()
    await _make_overdue(created["id"])

    await process(job_body(JobType.SLA_SCAN, {}, "sla-scan:test-1"))
    await process(job_body(JobType.SLA_SCAN, {}, "sla-scan:test-2"))  # next minute: nothing new
    await process(job_body(JobType.SLA_SCAN, {}, "sla-scan:test-1"))  # duplicate delivery: skipped

    ticket = body(await client.get(f"{API}/tickets/{created['id']}", headers=agent))
    assert ticket["sla_state"] == "breached"
    assert await _count(created["id"], TicketEventType.SLA_BREACHED) == 1

    async with SessionFactory() as s:
        alerts = await s.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.ticket_id == uuid.UUID(created["id"]), Notification.kind == "ticket.sla_breached")
        )
    assert alerts and alerts >= 1  # assignee + managers
    breaching = body(await client.get(f"{API}/tickets?view=breaching_soon&limit=100", headers=agent))["items"]
    assert created["id"] in {t["id"] for t in breaching}
    await jobs.run()


async def test_csv_export_lands_in_s3(client: AsyncClient, lead: dict[str, str], jobs: Jobs) -> None:
    today = date.today()
    started = await client.post(
        f"{API}/reports/exports", headers=lead, json={"from_date": str(today - timedelta(days=90)), "to_date": str(today)}
    )
    assert started.status_code == 202 and started.json()["status"] == "pending"
    queued = [json.loads(b)["type"] for b in jobs.bodies]
    assert queued == ["export_csv"]
    await jobs.run()

    export = body(await client.get(f"{API}/reports/exports/{started.json()['id']}", headers=lead))
    assert export["status"] == "ready" and export["row_count"] >= 60
    async with AsyncClient() as s3:
        csv_text = (await s3.get(export["download_url"])).text
    assert csv_text.splitlines()[0].startswith("number,subject,status")
    assert len(csv_text.splitlines()) == export["row_count"] + 1


async def test_export_range_is_validated(client: AsyncClient, lead: dict[str, str], agent: dict[str, str]) -> None:
    bad = await client.post(f"{API}/reports/exports", headers=lead, json={"from_date": "2026-05-01", "to_date": "2026-01-01"})
    assert bad.status_code == 422
    assert (
        await client.post(f"{API}/reports/exports", headers=agent, json={"from_date": "2026-01-01", "to_date": "2026-01-02"})
    ).status_code == 403


async def test_dashboard_numbers(client: AsyncClient, lead: dict[str, str]) -> None:
    dash = body(await client.get(f"{API}/reports/dashboard", headers=lead))
    assert dash["open_total"] == sum(dash["open_by_status"].values())
    assert len(dash["volume"]) == 14
    assert {a["full_name"] for a in dash["agent_load"]} >= {"Priya Natarajan", "Sam Okafor"}
