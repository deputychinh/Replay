import { TicketPriority, TicketStatus } from '@relay/api-client';
import { copy } from '../../lib/copy';
import './badge.css';

/** Status → colour family: the only place this mapping exists. */
const STATUS_TONE: Record<TicketStatus, string> = {
  [TicketStatus.NEW]: 'new',
  [TicketStatus.OPEN]: 'open',
  [TicketStatus.PENDING_CUSTOMER]: 'waiting',
  [TicketStatus.ON_HOLD]: 'waiting',
  [TicketStatus.SOLVED]: 'done',
  [TicketStatus.CLOSED]: 'closed',
};

export function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`badge badge--${STATUS_TONE[status]}`}>{copy.status[status]}</span>;
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return <span className={`badge badge--priority badge--${priority}`}>{copy.priority[priority]}</span>;
}

export function Tag({ children }: { children: string }) {
  return <span className="badge badge--tag">{children}</span>;
}
