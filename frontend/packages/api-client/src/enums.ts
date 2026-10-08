// Generated from openapi.json by scripts/gen-enums.mjs — do not edit.

export const ErrorCode = {
  VALIDATION_ERROR: "VALIDATION_ERROR",
  UNAUTHORIZED: "UNAUTHORIZED",
  FORBIDDEN: "FORBIDDEN",
  NOT_FOUND: "NOT_FOUND",
  CONFLICT: "CONFLICT",
  INVALID_TRANSITION: "INVALID_TRANSITION",
  RATE_LIMITED: "RATE_LIMITED",
  INTERNAL_ERROR: "INTERNAL_ERROR",
} as const;
export type ErrorCode = (typeof ErrorCode)[keyof typeof ErrorCode];

export const EventName = {
  TICKET_CREATED: "ticket.created",
  TICKET_UPDATED: "ticket.updated",
  TICKET_REPLY_ADDED: "ticket.reply_added",
  TICKET_SLA_WARNING: "ticket.sla_warning",
  TICKET_SLA_BREACHED: "ticket.sla_breached",
  NOTIFICATION_CREATED: "notification.created",
  EXPORT_READY: "export.ready",
  AGENT_TYPING: "agent.typing",
} as const;
export type EventName = (typeof EventName)[keyof typeof EventName];

export const ExportStatus = {
  PENDING: "pending",
  RUNNING: "running",
  READY: "ready",
  FAILED: "failed",
} as const;
export type ExportStatus = (typeof ExportStatus)[keyof typeof ExportStatus];

export const MessageKind = {
  PUBLIC_REPLY: "public_reply",
  INTERNAL_NOTE: "internal_note",
} as const;
export type MessageKind = (typeof MessageKind)[keyof typeof MessageKind];

export const Role = {
  OWNER: "owner",
  ADMIN: "admin",
  AGENT: "agent",
  CUSTOMER: "customer",
} as const;
export type Role = (typeof Role)[keyof typeof Role];

export const SlaState = {
  ACTIVE: "active",
  PAUSED: "paused",
  MET: "met",
  BREACHED: "breached",
} as const;
export type SlaState = (typeof SlaState)[keyof typeof SlaState];

export const TicketChannel = {
  PORTAL: "portal",
  EMAIL: "email",
  API: "api",
} as const;
export type TicketChannel = (typeof TicketChannel)[keyof typeof TicketChannel];

export const TicketEventType = {
  CREATED: "created",
  STATUS_CHANGED: "status_changed",
  PRIORITY_CHANGED: "priority_changed",
  ASSIGNED: "assigned",
  REPLIED: "replied",
  NOTE_ADDED: "note_added",
  SLA_WARNING: "sla_warning",
  SLA_BREACHED: "sla_breached",
} as const;
export type TicketEventType = (typeof TicketEventType)[keyof typeof TicketEventType];

export const TicketPriority = {
  LOW: "low",
  NORMAL: "normal",
  HIGH: "high",
  URGENT: "urgent",
} as const;
export type TicketPriority = (typeof TicketPriority)[keyof typeof TicketPriority];

export const TicketSort = {
  NEWEST: "newest",
  OLDEST: "oldest",
  PRIORITY: "priority",
  SLA_DUE: "sla_due",
} as const;
export type TicketSort = (typeof TicketSort)[keyof typeof TicketSort];

export const TicketStatus = {
  NEW: "new",
  OPEN: "open",
  PENDING_CUSTOMER: "pending_customer",
  ON_HOLD: "on_hold",
  SOLVED: "solved",
  CLOSED: "closed",
} as const;
export type TicketStatus = (typeof TicketStatus)[keyof typeof TicketStatus];

export const TicketView = {
  MINE: "mine",
  UNASSIGNED: "unassigned",
  ALL: "all",
  BREACHING_SOON: "breaching_soon",
} as const;
export type TicketView = (typeof TicketView)[keyof typeof TicketView];
