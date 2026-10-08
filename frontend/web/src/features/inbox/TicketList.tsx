import { useVirtualizer } from '@tanstack/react-virtual';
import { useEffect, useRef } from 'react';
import { Link } from 'react-router';
import { Avatar } from '../../components/avatar/Avatar';
import { PriorityBadge, StatusBadge } from '../../components/badge/Badge';
import { SlaTimer } from '../../components/sla-timer/SlaTimer';
import { copy } from '../../lib/copy';
import { formatRelative } from '../../lib/format';
import type { Ticket } from '../../queries/tickets';
import './ticket-list.css';

const ROW_HEIGHT = 76;

interface Props {
  tickets: Ticket[];
  activeId?: string;
  selected: Set<string>;
  onToggle: (id: string) => void;
  hrefFor: (id: string) => string;
  hasMore: boolean;
  onLoadMore: () => void;
}

/** Virtualised: only the visible rows are in the DOM, so long queues stay fast. */
export function TicketList({ tickets, activeId, selected, onToggle, hrefFor, hasMore, onLoadMore }: Props) {
  const scroller = useRef<HTMLDivElement>(null);
  const virtual = useVirtualizer({
    count: tickets.length,
    getScrollElement: () => scroller.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
  });
  const items = virtual.getVirtualItems();
  const last = items[items.length - 1];

  useEffect(() => {
    if (hasMore && last && last.index >= tickets.length - 10) onLoadMore();
  }, [hasMore, last, tickets.length, onLoadMore]);

  useEffect(() => {
    const index = tickets.findIndex((t) => t.id === activeId);
    if (index >= 0) virtual.scrollToIndex(index, { align: 'auto' });
  }, [activeId, tickets, virtual]);

  return (
    <div className="ticket-list" ref={scroller}>
      <ul className="ticket-list__rows" role="list" style={{ height: virtual.getTotalSize() }}>
        {items.map((row) => {
          const t = tickets[row.index]!;
          const active = t.id === activeId;
          return (
            <li
              key={t.id}
              className={`ticket-list__row${active ? ' ticket-list__row--active' : ''}`}
              style={{ transform: `translateY(${row.start}px)`, height: ROW_HEIGHT }}
            >
              <input
                type="checkbox"
                className="ticket-list__check"
                aria-label={`Select #${t.number}`}
                checked={selected.has(t.id)}
                onChange={() => onToggle(t.id)}
              />
              <Link className="ticket-list__link" to={hrefFor(t.id)} aria-current={active ? 'true' : undefined}>
                <span className="ticket-list__top">
                  <span className="ticket-list__number">#{t.number}</span>
                  <span className="ticket-list__subject">{t.subject}</span>
                  <time className="ticket-list__time" dateTime={t.updated_at}>{formatRelative(t.updated_at)}</time>
                </span>
                <span className="ticket-list__meta">
                  <span className="ticket-list__requester">
                    {t.requester.full_name}
                    {t.requester.company ? ` · ${t.requester.company}` : ''}
                  </span>
                  <StatusBadge status={t.status} />
                  <PriorityBadge priority={t.priority} />
                  <SlaTimer ticket={t} compact />
                  {t.assignee ? (
                    <span className="ticket-list__assignee" title={t.assignee.full_name}>
                      <Avatar name={t.assignee.full_name} staff size="small" />
                    </span>
                  ) : (
                    <span className="ticket-list__assignee ticket-list__assignee--none">{copy.common.unassigned}</span>
                  )}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
