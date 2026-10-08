"""Every closed set of values in Relay — the single source.

The front end gets the same values through OpenAPI: `make gen-client` turns
these enums into `as const` objects in frontend/packages/api-client.
"""

from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    AGENT = "agent"
    CUSTOMER = "customer"


class TicketStatus(StrEnum):
    NEW = "new"
    OPEN = "open"
    PENDING_CUSTOMER = "pending_customer"
    ON_HOLD = "on_hold"
    SOLVED = "solved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TicketChannel(StrEnum):
    PORTAL = "portal"
    EMAIL = "email"
    API = "api"


class MessageKind(StrEnum):
    PUBLIC_REPLY = "public_reply"
    INTERNAL_NOTE = "internal_note"


class SlaTarget(StrEnum):
    FIRST_RESPONSE = "first_response"
    RESOLUTION = "resolution"


class SlaState(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    MET = "met"
    BREACHED = "breached"


class TicketView(StrEnum):
    MINE = "mine"
    UNASSIGNED = "unassigned"
    ALL = "all"
    BREACHING_SOON = "breaching_soon"


class TicketSort(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"
    PRIORITY = "priority"
    SLA_DUE = "sla_due"


class TicketEventType(StrEnum):
    """Audit log entries on a ticket."""

    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    ASSIGNED = "assigned"
    REPLIED = "replied"
    NOTE_ADDED = "note_added"
    SLA_WARNING = "sla_warning"
    SLA_BREACHED = "sla_breached"


class JobType(StrEnum):
    SEND_EMAIL = "send_email"
    SLA_SCAN = "sla_scan"
    AUTO_CLOSE = "auto_close"
    EXPORT_CSV = "export_csv"
    AUTO_ASSIGN = "auto_assign"


class EventName(StrEnum):
    """Real-time events pushed to the console over WebSocket."""

    TICKET_CREATED = "ticket.created"
    TICKET_UPDATED = "ticket.updated"
    REPLY_ADDED = "ticket.reply_added"
    SLA_WARNING = "ticket.sla_warning"
    SLA_BREACHED = "ticket.sla_breached"
    NOTIFICATION = "notification.created"
    EXPORT_READY = "export.ready"
    AGENT_TYPING = "agent.typing"


class ExportStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


STAFF_ROLES: frozenset[Role] = frozenset({Role.OWNER, Role.ADMIN, Role.AGENT})
MANAGER_ROLES: frozenset[Role] = frozenset({Role.OWNER, Role.ADMIN})
