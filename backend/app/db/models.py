"""Import every model once, so Alembic and the tenant test see all tables."""

from app.jobs.models import ProcessedJob
from app.modules.attachments.models import Attachment
from app.modules.canned_replies.models import CannedReply
from app.modules.messages.models import Message
from app.modules.notifications.models import Notification
from app.modules.organizations.models import BusinessCalendar, Holiday, Organization
from app.modules.reports.models import Export
from app.modules.sla_policies.models import SlaPolicy
from app.modules.teams.models import Team, TeamMember
from app.modules.tickets.models import Ticket, TicketEvent
from app.modules.users.models import RefreshToken, User

__all__ = [
    "Attachment",
    "BusinessCalendar",
    "CannedReply",
    "Export",
    "Holiday",
    "Message",
    "Notification",
    "Organization",
    "ProcessedJob",
    "RefreshToken",
    "SlaPolicy",
    "Team",
    "TeamMember",
    "Ticket",
    "TicketEvent",
    "User",
]
