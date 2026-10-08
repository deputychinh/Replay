"""Dashboard numbers (cached briefly) and CSV export jobs."""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import Date, cast, func, select

from app.cache import keys
from app.cache.cache import cached
from app.common.constants import DASHBOARD_CACHE_TTL_SECONDS
from app.common.enums import STAFF_ROLES, SlaState
from app.db.tenant import TenantRepository
from app.modules.reports.models import Export
from app.modules.tickets.models import Ticket
from app.modules.tickets.rules import OPEN_STATUSES
from app.modules.users.models import User

WINDOW_DAYS = 30
VOLUME_DAYS = 14


class ExportRepository(TenantRepository[Export]):
    model = Export


class DashboardQueries(TenantRepository[Ticket]):
    model = Ticket

    async def summary(self) -> dict[str, Any]:
        return dict(await cached(keys.dashboard(self.org_id), DASHBOARD_CACHE_TTL_SECONDS, self._compute))

    async def _compute(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        since = now - timedelta(days=WINDOW_DAYS)
        s, t = self.session, Ticket

        by_status = dict(
            (await s.execute(self.scoped(t.status, func.count()).where(t.status.in_(OPEN_STATUSES)).group_by(t.status))).all()
        )

        minutes = func.extract("epoch", t.first_responded_at - t.created_at) / 60
        p50, p90 = (
            await s.execute(
                self.scoped(
                    func.percentile_cont(0.5).within_group(minutes),
                    func.percentile_cont(0.9).within_group(minutes),
                ).where(t.first_responded_at.is_not(None), t.created_at >= since)
            )
        ).one()

        met, breached = (
            await s.execute(
                self.scoped(
                    func.count().filter(t.sla_state == SlaState.MET),
                    func.count().filter(t.sla_state == SlaState.BREACHED),
                ).where(t.solved_at >= since)
            )
        ).one()

        breaching_now = await s.scalar(
            self.scoped(func.count()).where(t.status.in_(OPEN_STATUSES), t.sla_state == SlaState.BREACHED)
        )

        day = cast(t.created_at, Date)
        volume_rows = (
            await s.execute(
                self.scoped(day, func.count())
                .where(t.created_at >= now - timedelta(days=VOLUME_DAYS))
                .group_by(day)
                .order_by(day)
            )
        ).all()
        volume = {d.isoformat(): n for d, n in volume_rows}
        start = (now - timedelta(days=VOLUME_DAYS - 1)).date()

        load_rows = (
            await s.execute(
                select(User.id, User.full_name, func.count(t.id))
                .outerjoin(t, (t.assignee_id == User.id) & t.status.in_(OPEN_STATUSES))
                .where(User.org_id == self.org_id, User.role.in_(STAFF_ROLES), User.is_active.is_(True))
                .group_by(User.id, User.full_name)
                .order_by(func.count(t.id).desc())
            )
        ).all()

        return {
            "open_by_status": {str(k): v for k, v in by_status.items()},
            "open_total": sum(by_status.values()),
            "breached_open": int(breaching_now or 0),
            "first_response_p50_minutes": round(p50, 1) if p50 is not None else None,
            "first_response_p90_minutes": round(p90, 1) if p90 is not None else None,
            "sla_attainment_percent": round(met * 100 / (met + breached), 1) if met + breached else None,
            "volume": [
                {"day": d, "count": volume.get(d, 0)}
                for d in ((start + timedelta(days=i)).isoformat() for i in range(VOLUME_DAYS))
            ],
            "agent_load": [{"user_id": str(uid), "full_name": name, "open": count} for uid, name, count in load_rows],
            "window_days": WINDOW_DAYS,
        }


def export_rows_query(org_id: uuid.UUID, from_date: date, to_date: date) -> Any:
    requester = User.__table__.alias("requester")
    assignee = User.__table__.alias("assignee")
    return (
        select(
            Ticket.number,
            Ticket.subject,
            Ticket.status,
            Ticket.priority,
            requester.c.full_name,
            requester.c.company,
            assignee.c.full_name,
            Ticket.sla_state,
            Ticket.created_at,
            Ticket.first_responded_at,
            Ticket.solved_at,
        )
        .join(requester, requester.c.id == Ticket.requester_id)
        .outerjoin(assignee, assignee.c.id == Ticket.assignee_id)
        .where(Ticket.org_id == org_id, cast(Ticket.created_at, Date) >= from_date, cast(Ticket.created_at, Date) <= to_date)
        .order_by(Ticket.number)
    )


EXPORT_HEADER = [
    "number",
    "subject",
    "status",
    "priority",
    "requester",
    "company",
    "assignee",
    "sla_state",
    "created_at",
    "first_responded_at",
    "solved_at",
]
