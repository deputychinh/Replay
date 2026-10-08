import { useParams } from 'react-router';
import { StatusBadge } from '../../components/badge/Badge';
import { ErrorState, Loading } from '../../components/empty-state/EmptyState';
import { copy } from '../../lib/copy';
import { useMessages, useTicket } from '../../queries/tickets';
import { Composer } from '../ticket/Composer';
import { Thread } from '../ticket/Thread';

export function PortalTicketPage() {
  const { ticketId = '' } = useParams();
  const ticket = useTicket(ticketId);
  const messages = useMessages(ticketId);
  if (ticket.isPending) return <Loading />;
  if (ticket.isError) return <ErrorState error={ticket.error} />;
  const t = ticket.data;
  return (
    <section className="portal__section">
      <p className="portal__number">#{t.number}</p>
      <div className="portal__head">
        <h1 className="portal__title">{t.subject}</h1>
        <StatusBadge status={t.status} />
      </div>
      {messages.data ? <Thread messages={messages.data} perspective="customer" /> : <Loading />}
      {t.status === 'closed' ? <p className="portal__lead">{copy.ticket.closedNotice}</p> : <Composer ticketId={t.id} staff={false} />}
    </section>
  );
}
