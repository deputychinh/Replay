import { useEffect, useState } from 'react';
import { slaInfo } from '../../lib/sla';
import type { Ticket } from '../../queries/tickets';
import './sla-timer.css';

const TICK_MS = 30_000;

/** Live countdown to the nearest open SLA target. */
export function SlaTimer({ ticket, compact }: { ticket: Ticket; compact?: boolean }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(timer);
  }, []);
  const info = slaInfo(ticket, now);
  return (
    <span className={`sla-timer sla-timer--${info.tone}${compact ? ' sla-timer--compact' : ''}`} title={info.dueAt ?? undefined}>
      {info.label}
    </span>
  );
}
