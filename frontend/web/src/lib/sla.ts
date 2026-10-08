// What to show for a ticket's SLA right now: the nearest open target and how close it is.
import { SlaState, type Schemas } from '@relay/api-client';
import { copy } from './copy';
import { formatDuration } from './format';

/** Matches SLA_WARNING_MINUTES in backend/app/common/constants.py. */
export const SLA_WARNING_MINUTES = 30;

export type SlaTone = 'ok' | 'warning' | 'breached' | 'paused' | 'done';

export interface SlaInfo {
  tone: SlaTone;
  label: string;
  dueAt: string | null;
}

type TicketSla = Pick<
  Schemas['TicketOut'],
  'sla_state' | 'first_response_due_at' | 'resolution_due_at' | 'first_responded_at'
>;

export function slaInfo(ticket: TicketSla, now = Date.now()): SlaInfo {
  if (ticket.sla_state === SlaState.PAUSED) return { tone: 'paused', label: copy.sla[SlaState.PAUSED], dueAt: null };
  if (ticket.sla_state === SlaState.MET) return { tone: 'done', label: copy.sla[SlaState.MET], dueAt: null };

  const due = !ticket.first_responded_at ? ticket.first_response_due_at : ticket.resolution_due_at;
  if (!due) return { tone: 'done', label: copy.sla.done, dueAt: null };
  const minutes = (new Date(due).getTime() - now) / 60000;
  if (minutes < 0) return { tone: 'breached', label: copy.sla.overdue(formatDuration(-minutes)), dueAt: due };
  if (ticket.sla_state === SlaState.BREACHED) {
    // An earlier target was missed; the record stays breached even if the next one is still ahead.
    return { tone: 'breached', label: copy.sla[SlaState.BREACHED], dueAt: due };
  }
  return {
    tone: minutes <= SLA_WARNING_MINUTES ? 'warning' : 'ok',
    label: copy.sla.dueIn(formatDuration(minutes)),
    dueAt: due,
  };
}
