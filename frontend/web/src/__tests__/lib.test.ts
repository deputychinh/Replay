import { SlaState } from '@relay/api-client';
import { fillPlaceholders } from '../features/ticket/Composer';
import { formatDuration, formatRelative, initials } from '../lib/format';
import { SLA_WARNING_MINUTES, slaInfo } from '../lib/sla';

const NOW = Date.parse('2026-10-08T12:00:00Z');
const at = (minutes: number) => new Date(NOW + minutes * 60000).toISOString();
const base = { sla_state: SlaState.ACTIVE, first_response_due_at: at(120), resolution_due_at: at(600), first_responded_at: null };

describe('slaInfo', () => {
  it('tracks first response until the agent answers', () => {
    expect(slaInfo(base, NOW)).toEqual({ tone: 'ok', label: 'due in 2h', dueAt: at(120) });
  });

  it('switches to resolution after the first response', () => {
    expect(slaInfo({ ...base, first_responded_at: at(-5) }, NOW).label).toBe('due in 10h');
  });

  it('warns inside the warning window', () => {
    expect(slaInfo({ ...base, first_response_due_at: at(SLA_WARNING_MINUTES - 1) }, NOW).tone).toBe('warning');
  });

  it('shows how late an overdue target is', () => {
    expect(slaInfo({ ...base, first_response_due_at: at(-95) }, NOW)).toMatchObject({ tone: 'breached', label: '1h 35m overdue' });
  });

  it('keeps a breach visible even when the next target is ahead', () => {
    expect(slaInfo({ ...base, sla_state: SlaState.BREACHED }, NOW)).toMatchObject({ tone: 'breached', label: 'Breached' });
  });

  it('shows paused and met states', () => {
    expect(slaInfo({ ...base, sla_state: SlaState.PAUSED }, NOW).tone).toBe('paused');
    expect(slaInfo({ ...base, sla_state: SlaState.MET }, NOW).tone).toBe('done');
  });
});

describe('format helpers', () => {
  it.each([[0, '0m'], [45, '45m'], [60, '1h'], [95, '1h 35m'], [1440, '1d'], [3000, '2d 2h']])('formatDuration(%i) = %s', (m, text) => {
    expect(formatDuration(m)).toBe(text);
  });

  it('formats relative times', () => {
    expect(formatRelative(at(-180), NOW)).toBe('3 hours ago');
    expect(formatRelative(at(-0.2), NOW)).toBe('just now');
    expect(formatRelative(at(60 * 24 * 2), NOW)).toBe('in 2 days');
  });

  it('builds initials', () => {
    expect(initials('Priya Natarajan')).toBe('PN');
    expect(initials('  dana  ')).toBe('D');
  });
});

describe('canned reply placeholders', () => {
  it('fills known keys and leaves unknown ones', () => {
    const text = 'Hi {{customer.name}}, #{{ ticket.number }} is fixed. {{unknown}} — {{agent.name}}';
    expect(fillPlaceholders(text, { 'customer.name': 'Dana', 'ticket.number': '42', 'agent.name': 'Priya' }))
      .toBe('Hi Dana, #42 is fixed. {{unknown}} — Priya');
  });
});
