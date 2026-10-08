import { Link, useParams } from 'react-router';
import { StatusBadge } from '../../components/badge/Badge';
import { EmptyState, ErrorState, Loading } from '../../components/empty-state/EmptyState';
import { copy } from '../../lib/copy';
import { formatRelative } from '../../lib/format';
import { useTickets } from '../../queries/tickets';

export function MyTicketsPage() {
  const { org = '' } = useParams();
  const query = useTickets({});
  if (query.isPending) return <Loading />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  const tickets = query.data.pages.flatMap((p) => p.items);
  return (
    <section className="portal__section">
      <div className="portal__head">
        <h1 className="portal__title">{copy.portal.myTickets}</h1>
        <Link className="portal__cta" to={`/portal/${org}/new`}>{copy.portal.newTicket}</Link>
      </div>
      {tickets.length === 0 ? <EmptyState title={copy.portal.empty} /> : (
        <ul className="portal__tickets" role="list">
          {tickets.map((t) => (
            <li key={t.id}>
              <Link className="portal__ticket" to={`/portal/${org}/tickets/${t.id}`}>
                <span className="portal__number">#{t.number}</span>
                <span className="portal__subject">{t.subject}</span>
                <StatusBadge status={t.status} />
                <time className="portal__time" dateTime={t.updated_at}>{formatRelative(t.updated_at)}</time>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {query.hasNextPage && <button type="button" className="portal__more" onClick={() => void query.fetchNextPage()}>{copy.common.loadMore}</button>}
    </section>
  );
}
