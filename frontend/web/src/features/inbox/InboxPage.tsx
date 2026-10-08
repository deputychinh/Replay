import { EventName, TicketPriority, TicketSort, TicketStatus, TicketView } from '@relay/api-client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useAuth } from '../../app/auth';
import { Button } from '../../components/button/Button';
import { EmptyState, ErrorState, Loading } from '../../components/empty-state/EmptyState';
import { useToast } from '../../components/toast/Toast';
import { copy } from '../../lib/copy';
import { useLiveEvent } from '../../lib/realtime';
import { useBulkUpdate, useTickets, type TicketFilters } from '../../queries/tickets';
import { useStaff } from '../../queries/workspace';
import { TicketPanel } from '../ticket/TicketPanel';
import { TicketList } from './TicketList';
import './inbox.css';

const SORT_LABELS: Record<TicketSort, string> = {
  [TicketSort.NEWEST]: copy.inbox.sortRecent,
  [TicketSort.OLDEST]: copy.inbox.sortOldest,
  [TicketSort.PRIORITY]: copy.inbox.sortPriority,
  [TicketSort.SLA_DUE]: copy.inbox.sortSla,
};
const TYPING_SHOWN_MS = 5000;

export function InboxPage() {
  const { view = TicketView.MINE, ticketId } = useParams();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const { session } = useAuth();
  const toast = useToast();
  const staff = useStaff();
  const bulk = useBulkUpdate();
  const composer = useRef<HTMLTextAreaElement>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState(params.get('q') ?? '');
  const [typing, setTyping] = useState<{ ticketId: string; name: string } | null>(null);

  const filters: TicketFilters = useMemo(() => ({
    view: view as TicketView,
    status: (params.get('status') as TicketStatus) || undefined,
    priority: (params.get('priority') as TicketPriority) || undefined,
    q: params.get('q') || undefined,
    sort: (params.get('sort') as TicketSort) || (view === TicketView.BREACHING_SOON ? TicketSort.SLA_DUE : TicketSort.NEWEST),
  }), [view, params]);

  const query = useTickets(filters);
  const tickets = useMemo(() => query.data?.pages.flatMap((p) => p.items) ?? [], [query.data]);
  const hrefFor = useCallback((id: string) => `/console/inbox/${view}/${id}?${params.toString()}`, [view, params]);

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  useEffect(() => {
    const timer = setTimeout(() => { if (search !== (params.get('q') ?? '')) setParam('q', search.trim()); }, 300);
    return () => clearTimeout(timer);
  });

  useLiveEvent((event) => {
    if (event.event !== EventName.AGENT_TYPING || event.data.user_id === session?.user.id) return;
    const name = staff.data?.find((u) => u.id === event.data.user_id)?.full_name ?? 'A teammate';
    setTyping({ ticketId: String(event.data.ticket_id), name });
    setTimeout(() => setTyping(null), TYPING_SHOWN_MS);
  });

  // Keyboard: j / k move, a assign to me, r reply.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || event.metaKey || event.ctrlKey) return;
      const index = tickets.findIndex((t) => t.id === ticketId);
      if (event.key === 'j' || event.key === 'k') {
        const next = tickets[Math.min(tickets.length - 1, Math.max(0, index + (event.key === 'j' ? 1 : -1)))];
        if (next) navigate(hrefFor(next.id));
      } else if (event.key === 'a' && ticketId && session) {
        bulk.mutate({ ids: [ticketId], assignee_id: session.user.id, unassign: false });
      } else if (event.key === 'r') {
        event.preventDefault();
        composer.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [tickets, ticketId, navigate, hrefFor, bulk, session]);

  const toggle = (id: string) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const runBulk = (body: { assignee_id?: string; status?: TicketStatus }) =>
    bulk.mutate({ ids: [...selected], unassign: false, ...body }, {
      onSuccess: (r) => { toast(`${r.updated} tickets updated`); setSelected(new Set()); },
      onError: (e) => toast(e.message, 'error'),
    });

  return (
    <div className="inbox">
      <section className="inbox__list" aria-label={copy.views[view as TicketView]}>
        <header className="inbox__header">
          <h1 className="inbox__title">{copy.views[view as TicketView]}</h1>
          <input
            className="inbox__search"
            type="search"
            aria-label={copy.common.search}
            placeholder={copy.inbox.searchPlaceholder}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="inbox__filters">
            <select aria-label={copy.ticket.status} className="inbox__filter" value={filters.status ?? ''} onChange={(e) => setParam('status', e.target.value)}>
              <option value="">{copy.inbox.anyStatus}</option>
              {Object.values(TicketStatus).map((s) => <option key={s} value={s}>{copy.status[s]}</option>)}
            </select>
            <select aria-label={copy.ticket.priority} className="inbox__filter" value={filters.priority ?? ''} onChange={(e) => setParam('priority', e.target.value)}>
              <option value="">{copy.inbox.anyPriority}</option>
              {Object.values(TicketPriority).map((p) => <option key={p} value={p}>{copy.priority[p]}</option>)}
            </select>
            <select aria-label="Sort" className="inbox__filter" value={filters.sort} onChange={(e) => setParam('sort', e.target.value)}>
              {Object.values(TicketSort).map((s) => <option key={s} value={s}>{SORT_LABELS[s]}</option>)}
            </select>
          </div>
          {selected.size > 0 && session && (
            <div className="inbox__bulk" role="toolbar" aria-label="Bulk actions">
              <span>{copy.inbox.selected(selected.size)}</span>
              <Button size="small" onClick={() => runBulk({ assignee_id: session.user.id })}>{copy.inbox.assignToMe}</Button>
              <Button size="small" onClick={() => runBulk({ status: TicketStatus.SOLVED })}>{copy.inbox.markSolved}</Button>
              <Button size="small" variant="ghost" onClick={() => setSelected(new Set())}>{copy.inbox.clear}</Button>
            </div>
          )}
        </header>
        {query.isPending ? <Loading /> : query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : tickets.length === 0 ? (
          <EmptyState title={copy.inbox.empty} hint={copy.inbox.emptyHint} />
        ) : (
          <TicketList
            tickets={tickets}
            activeId={ticketId}
            selected={selected}
            onToggle={toggle}
            hrefFor={hrefFor}
            hasMore={Boolean(query.hasNextPage) && !query.isFetchingNextPage}
            onLoadMore={() => void query.fetchNextPage()}
          />
        )}
      </section>
      <div className="inbox__detail">
        {ticketId ? (
          <TicketPanel key={ticketId} ref={composer} ticketId={ticketId} typing={typing?.ticketId === ticketId ? typing.name : null} />
        ) : (
          <EmptyState title={copy.inbox.select} hint={copy.ticket.shortcuts} />
        )}
      </div>
    </div>
  );
}
