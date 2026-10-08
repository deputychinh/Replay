"""Job type → handler. Each handler gets the payload and a unit of work."""

from collections.abc import Awaitable, Callable
from typing import Any

from app.common.enums import JobType
from app.db.unit_of_work import UnitOfWork

Handler = Callable[[dict[str, Any], UnitOfWork], Awaitable[None]]


def handlers() -> dict[JobType, Handler]:
    from app.modules.automations import handlers as automation
    from app.modules.notifications.email import send_email
    from app.modules.reports.export import export_csv

    return {
        JobType.SEND_EMAIL: send_email,
        JobType.AUTO_ASSIGN: automation.auto_assign,
        JobType.SLA_SCAN: automation.sla_scan,
        JobType.AUTO_CLOSE: automation.auto_close,
        JobType.EXPORT_CSV: export_csv,
    }
