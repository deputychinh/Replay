import { TicketPriority } from '@relay/api-client';
import { useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router';
import { Button } from '../../components/button/Button';
import { SelectField, TextArea, TextField } from '../../components/field/Field';
import { useToast } from '../../components/toast/Toast';
import { copy } from '../../lib/copy';
import { ALLOWED_TYPES, MAX_UPLOAD_BYTES } from '../../lib/uploads';
import { useCreateTicket } from '../../queries/tickets';
import { uploadFile } from '../../queries/workspace';

export function NewTicketPage() {
  const { org = '' } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const create = useCreateTicket();
  const [form, setForm] = useState({ subject: '', body: '', priority: TicketPriority.NORMAL as TicketPriority });
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const attachment_ids = await Promise.all(files.map(uploadFile));
      const ticket = await create.mutateAsync({ ...form, attachment_ids });
      toast(copy.portal.created(ticket.number));
      navigate(`/portal/${org}/tickets/${ticket.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : copy.errors.generic);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="portal__section">
      <h1 className="portal__title">{copy.portal.newTicket}</h1>
      <form className="portal__form" onSubmit={(e) => void submit(e)}>
        {error && <p className="portal__error" role="alert">{error}</p>}
        <TextField label={copy.portal.subject} value={form.subject} required minLength={3} maxLength={200}
          onChange={(e) => setForm({ ...form, subject: e.target.value })} />
        <TextArea label={copy.portal.description} value={form.body} required rows={8}
          onChange={(e) => setForm({ ...form, body: e.target.value })} />
        <SelectField label={copy.portal.priority} value={form.priority}
          options={Object.values(TicketPriority).map((p) => ({ value: p, label: copy.priority[p] }))}
          onChange={(e) => setForm({ ...form, priority: e.target.value as TicketPriority })} />
        <TextField label={copy.portal.attachments} type="file" multiple accept={ALLOWED_TYPES.join(',')}
          hint={copy.errors.fileSize}
          onChange={(e) => {
            const chosen = Array.from(e.target.files ?? []);
            if (chosen.some((f) => f.size > MAX_UPLOAD_BYTES)) return setError(copy.errors.fileSize);
            setFiles(chosen);
          }} />
        <Button type="submit" variant="primary" loading={busy}>{copy.portal.submit}</Button>
      </form>
    </section>
  );
}
