import { Role, TicketPriority, type Schemas } from '@relay/api-client';
import { useState } from 'react';
import { useAuth } from '../../app/auth';
import { PriorityBadge } from '../../components/badge/Badge';
import { Button } from '../../components/button/Button';
import { Loading } from '../../components/empty-state/EmptyState';
import { TextArea, TextField } from '../../components/field/Field';
import { useToast } from '../../components/toast/Toast';
import { copy } from '../../lib/copy';
import { useCalendar, useCannedReplies, useCreateCannedReply, useSaveCalendar, useSetSlaPolicy, useSlaPolicies } from '../../queries/workspace';
import './settings.css';

const toTime = (minutes: number) => `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;
const toMinutes = (time: string) => {
  const [h = '0', m = '0'] = time.split(':');
  return Number(h) * 60 + Number(m);
};

function SlaTargets({ canEdit }: { canEdit: boolean }) {
  const policies = useSlaPolicies();
  const save = useSetSlaPolicy();
  const toast = useToast();
  if (!policies.data) return <Loading />;
  return (
    <section className="settings__card">
      <h2 className="settings__heading">{copy.settings.sla}</h2>
      <p className="settings__lead">{copy.settings.slaLead}</p>
      <table className="settings__table">
        <thead>
          <tr><th scope="col">{copy.ticket.priority}</th><th scope="col">{copy.settings.firstResponse}</th><th scope="col">{copy.settings.resolution}</th></tr>
        </thead>
        <tbody>
          {policies.data.map((p) => (
            <tr key={p.priority}>
              <td><PriorityBadge priority={p.priority} /></td>
              {(['first_response_minutes', 'resolution_minutes'] as const).map((field) => (
                <td key={field}>
                  <input className="settings__number" type="number" min={5} defaultValue={p[field]} disabled={!canEdit}
                    aria-label={`${copy.priority[p.priority]} ${field}`}
                    onBlur={(e) => {
                      const value = Number(e.target.value);
                      if (value === p[field]) return;
                      save.mutate({ priority: p.priority as TicketPriority, body: { ...p, [field]: value } },
                        { onSuccess: () => toast(copy.settings.saved), onError: (err) => toast(err.message, 'error') });
                    }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function BusinessHours({ canEdit }: { canEdit: boolean }) {
  const calendar = useCalendar();
  const save = useSaveCalendar();
  const toast = useToast();
  const [draft, setDraft] = useState<Schemas['CalendarIn'] | null>(null);
  const value = draft ?? calendar.data;
  if (!value) return <Loading />;
  const setDay = (day: string, span: number[] | null) => {
    const hours = { ...value.weekly_hours };
    if (span) hours[day] = span;
    else delete hours[day];
    setDraft({ timezone: value.timezone, weekly_hours: hours });
  };
  return (
    <section className="settings__card">
      <h2 className="settings__heading">{copy.settings.hours}</h2>
      <p className="settings__lead">{copy.settings.hoursLead}</p>
      <TextField label={copy.settings.timezone} value={value.timezone} disabled={!canEdit}
        onChange={(e) => setDraft({ ...value, timezone: e.target.value })} />
      <ul className="settings__days" role="list">
        {copy.settings.days.map((name, index) => {
          const span = value.weekly_hours[String(index)];
          return (
            <li key={name} className="settings__day">
              <label className="settings__check">
                <input type="checkbox" checked={Boolean(span)} disabled={!canEdit}
                  onChange={(e) => setDay(String(index), e.target.checked ? [540, 1020] : null)} />
                {name}
              </label>
              {span ? (
                <>
                  <input type="time" className="settings__time" value={toTime(span[0]!)} disabled={!canEdit} aria-label={`${name} opens`}
                    onChange={(e) => setDay(String(index), [toMinutes(e.target.value), span[1]!])} />
                  <input type="time" className="settings__time" value={toTime(span[1]!)} disabled={!canEdit} aria-label={`${name} closes`}
                    onChange={(e) => setDay(String(index), [span[0]!, toMinutes(e.target.value)])} />
                </>
              ) : <span className="settings__closed">{copy.settings.closed}</span>}
            </li>
          );
        })}
      </ul>
      {canEdit && (
        <Button variant="primary" loading={save.isPending} disabled={!draft}
          onClick={() => draft && save.mutate(draft, {
            onSuccess: () => { setDraft(null); toast(copy.settings.saved); },
            onError: (e) => toast(e.message, 'error'),
          })}>
          {copy.common.save}
        </Button>
      )}
    </section>
  );
}

function CannedReplies({ canEdit }: { canEdit: boolean }) {
  const replies = useCannedReplies();
  const create = useCreateCannedReply();
  const [form, setForm] = useState({ title: '', body: '' });
  return (
    <section className="settings__card">
      <h2 className="settings__heading">{copy.settings.canned}</h2>
      <ul className="settings__replies" role="list">
        {replies.data?.map((r) => (
          <li key={r.id} className="settings__reply"><strong>{r.title}</strong><span>{r.body}</span></li>
        ))}
      </ul>
      {canEdit && (
        <form className="settings__form" onSubmit={(e) => {
          e.preventDefault();
          create.mutate(form, { onSuccess: () => setForm({ title: '', body: '' }) });
        }}>
          <TextField label={copy.settings.cannedTitle} value={form.title} required onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <TextArea label={copy.settings.cannedBody} value={form.body} required onChange={(e) => setForm({ ...form, body: e.target.value })}
            hint="{{customer.name}} · {{agent.name}} · {{ticket.number}}" />
          <Button type="submit" loading={create.isPending}>{copy.settings.cannedAdd}</Button>
        </form>
      )}
    </section>
  );
}

export function SettingsPage() {
  const { session } = useAuth();
  const canEdit = session?.user.role === Role.OWNER || session?.user.role === Role.ADMIN;
  return (
    <div className="settings">
      <h1 className="settings__title">{copy.settings.title}</h1>
      {!canEdit && <p className="settings__lead">{copy.settings.managersOnly}</p>}
      <SlaTargets canEdit={canEdit} />
      <BusinessHours canEdit={canEdit} />
      <CannedReplies canEdit={canEdit} />
    </div>
  );
}
