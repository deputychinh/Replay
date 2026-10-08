import { TicketPriority, type TicketStatus } from '@relay/api-client';
import { forwardRef, useState } from 'react';
import { PriorityBadge, StatusBadge, Tag } from '../../components/badge/Badge';
import { ErrorState, Loading } from '../../components/empty-state/EmptyState';
import { SlaTimer } from '../../components/sla-timer/SlaTimer';
import { useToast } from '../../components/toast/Toast';
import { useAuth } from '../../app/auth';
import { copy } from '../../lib/copy';
import { formatDateTime, formatRelative } from '../../lib/format';
import { useEvents, useMessages, useTicket, useUpdateTicket, type TicketDetail } from '../../queries/tickets';
import { useStaff } from '../../queries/workspace';
import { Composer } from './Composer';
import { Thread } from './Thread';
import './ticket-panel.css';

function Properties({ ticket }: { ticket: TicketDetail }) {
  const update = useUpdateTicket(ticket.id);
  const staff = useStaff();
  const toast = useToast();
  const events = useEvents(ticket.id, true);
  const [tags, setTags] = useState(ticket.tags.join(', '));

  const change = (body: Partial<Parameters<typeof update.mutate>[0]>) =>
    update.mutate({ unassign: false, ...body }, { onError: (e) => toast(e.message, 'error') });

  return (
    <aside className="ticket-panel__side" aria-label="Ticket properties">
      <dl className="ticket-panel__props">
        <dt className="ticket-panel__term">{copy.ticket.requester}</dt>
        <dd>
          {ticket.requester.full_name}
          {ticket.requester.company && <span className="ticket-panel__muted"> · {ticket.requester.company}</span>}
        </dd>

        <dt className="ticket-panel__term"><label htmlFor="prop-assignee">{copy.ticket.assignee}</label></dt>
        <dd>
          <select
            id="prop-assignee"
            className="ticket-panel__select"
            value={ticket.assignee?.id ?? ''}
            onChange={(e) => change(e.target.value ? { assignee_id: e.target.value } : { unassign: true })}
          >
            <option value="">{copy.common.unassigned}</option>
            {staff.data?.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
          </select>
        </dd>

        <dt className="ticket-panel__term"><label htmlFor="prop-status">{copy.ticket.status}</label></dt>
        <dd>
          <select
            id="prop-status"
            className="ticket-panel__select"
            value={ticket.status}
            disabled={ticket.allowed_statuses.length === 0}
            onChange={(e) => change({ status: e.target.value as TicketStatus })}
          >
            {[ticket.status, ...ticket.allowed_statuses].map((s) => <option key={s} value={s}>{copy.status[s]}</option>)}
          </select>
        </dd>

        <dt className="ticket-panel__term"><label htmlFor="prop-priority">{copy.ticket.priority}</label></dt>
        <dd>
          <select
            id="prop-priority"
            className="ticket-panel__select"
            value={ticket.priority}
            onChange={(e) => change({ priority: e.target.value as TicketPriority })}
          >
            {Object.values(TicketPriority).map((p) => <option key={p} value={p}>{copy.priority[p]}</option>)}
          </select>
        </dd>

        <dt className="ticket-panel__term"><label htmlFor="prop-tags">{copy.ticket.tags}</label></dt>
        <dd>
          <input
            id="prop-tags"
            className="ticket-panel__select"
            value={tags}
            placeholder={copy.ticket.tagsHint}
            onChange={(e) => setTags(e.target.value)}
            onBlur={() => {
              const next = tags.split(',').map((t) => t.trim()).filter(Boolean);
              if (next.join() !== ticket.tags.join()) change({ tags: next });
            }}
          />
        </dd>

        <dt className="ticket-panel__term">{copy.ticket.sla}</dt>
        <dd className="ticket-panel__sla">
          <SlaTimer ticket={ticket} />
          <span className="ticket-panel__muted">
            {copy.ticket.firstResponse}: {ticket.first_responded_at ? formatRelative(ticket.first_responded_at)
              : ticket.first_response_due_at ? formatDateTime(ticket.first_response_due_at) : '—'}
          </span>
          <span className="ticket-panel__muted">
            {copy.ticket.resolution}: {ticket.resolution_due_at ? formatDateTime(ticket.resolution_due_at) : copy.sla[ticket.sla_state]}
          </span>
        </dd>
      </dl>

      <h3 className="ticket-panel__heading">{copy.ticket.activity}</h3>
      <ol className="ticket-panel__events" role="list">
        {events.data?.map((e) => (
          <li key={e.id} className="ticket-panel__event">
            <span><strong>{e.actor?.full_name ?? copy.system}</strong> {copy.events[e.type]}</span>
            <time className="ticket-panel__muted" dateTime={e.created_at}>{formatRelative(e.created_at)}</time>
          </li>
        ))}
      </ol>
    </aside>
  );
}

export const TicketPanel = forwardRef<HTMLTextAreaElement, { ticketId: string; typing?: string | null }>(
  function TicketPanel({ ticketId, typing }, composerRef) {
    const { session } = useAuth();
    const ticket = useTicket(ticketId);
    const messages = useMessages(ticketId);

    if (ticket.isPending) return <Loading />;
    if (ticket.isError) return <ErrorState error={ticket.error} onRetry={() => void ticket.refetch()} />;
    const t = ticket.data;
    const closed = t.allowed_statuses.length === 0;

    return (
      <section className="ticket-panel" aria-labelledby="ticket-title">
        <header className="ticket-panel__header">
          <p className="ticket-panel__number">#{t.number}</p>
          <h1 className="ticket-panel__title" id="ticket-title">{t.subject}</h1>
          <div className="ticket-panel__badges">
            <StatusBadge status={t.status} />
            <PriorityBadge priority={t.priority} />
            {t.tags.map((tag) => <Tag key={tag}>{tag}</Tag>)}
            <span className="ticket-panel__muted">{copy.ticket.shortcuts}</span>
          </div>
        </header>
        <div className="ticket-panel__body">
          <div className="ticket-panel__conversation">
            {messages.data ? <Thread messages={messages.data} perspective="staff" /> : <Loading />}
            {typing && <p className="ticket-panel__typing">{copy.ticket.typing(typing)}</p>}
            {closed ? (
              <p className="ticket-panel__muted">{copy.ticket.closedNotice}</p>
            ) : (
              <Composer
                ref={composerRef}
                ticketId={t.id}
                staff
                placeholders={{
                  'customer.name': t.requester.full_name.split(' ')[0] ?? '',
                  'agent.name': session?.user.full_name ?? '',
                  'ticket.number': String(t.number),
                }}
              />
            )}
          </div>
          <Properties key={t.id + t.tags.join()} ticket={t} />
        </div>
      </section>
    );
  },
);
