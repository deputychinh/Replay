import { MessageKind, TicketStatus, type Schemas } from '@relay/api-client';
import { forwardRef, useState, type FormEvent } from 'react';
import { Button } from '../../components/button/Button';
import { useToast } from '../../components/toast/Toast';
import { copy } from '../../lib/copy';
import { sendTyping } from '../../lib/realtime';
import { ALLOWED_TYPES, MAX_UPLOAD_BYTES } from '../../lib/uploads';
import { useSendMessage } from '../../queries/tickets';
import { uploadFile, useCannedReplies } from '../../queries/workspace';
import './composer.css';

interface Props {
  ticketId: string;
  staff: boolean;
  placeholders?: Record<string, string>;
}

const STATUS_AFTER = [TicketStatus.PENDING_CUSTOMER, TicketStatus.OPEN, TicketStatus.ON_HOLD, TicketStatus.SOLVED];
const TYPING_THROTTLE_MS = 3000;

export function fillPlaceholders(text: string, values: Record<string, string>): string {
  return text.replace(/\{\{\s*([\w.]+)\s*\}\}/g, (match, key: string) => values[key] ?? match);
}

export const Composer = forwardRef<HTMLTextAreaElement, Props>(function Composer({ ticketId, staff, placeholders = {} }, ref) {
  const [kind, setKind] = useState<MessageKind>(MessageKind.PUBLIC_REPLY);
  const [body, setBody] = useState('');
  const [statusAfter, setStatusAfter] = useState<TicketStatus>(TicketStatus.PENDING_CUSTOMER);
  const [files, setFiles] = useState<File[]>([]);
  const [lastTyping, setLastTyping] = useState(0);
  const send = useSendMessage(ticketId);
  const canned = useCannedReplies();
  const toast = useToast();
  const note = kind === MessageKind.INTERNAL_NOTE;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!body.trim()) return;
    try {
      const attachment_ids = await Promise.all(files.map(uploadFile));
      const payload: Schemas['MessageCreate'] = { body, kind, attachment_ids };
      if (staff && !note) payload.status_after = statusAfter;
      await send.mutateAsync(payload);
      setBody('');
      setFiles([]);
    } catch (error) {
      toast(error instanceof Error ? error.message : copy.errors.generic, 'error');
    }
  };

  const pickFiles = (list: FileList | null) => {
    const chosen = Array.from(list ?? []);
    const bad = chosen.find((f) => !ALLOWED_TYPES.includes(f.type) || f.size > MAX_UPLOAD_BYTES);
    if (bad) return toast(bad.size > MAX_UPLOAD_BYTES ? copy.errors.fileSize : copy.errors.fileType, 'error');
    setFiles(chosen);
  };

  return (
    <form className={`composer${note ? ' composer--note' : ''}`} onSubmit={(e) => void submit(e)}>
      {staff && (
        <div className="composer__tabs" role="tablist">
          {[MessageKind.PUBLIC_REPLY, MessageKind.INTERNAL_NOTE].map((k) => (
            <button key={k} type="button" role="tab" aria-selected={kind === k} className="composer__tab" onClick={() => setKind(k)}>
              {k === MessageKind.PUBLIC_REPLY ? copy.ticket.reply : copy.ticket.note}
            </button>
          ))}
          {canned.data && canned.data.length > 0 && (
            <select
              className="composer__canned"
              aria-label={copy.ticket.canned}
              value=""
              onChange={(e) => {
                const reply = canned.data?.find((c) => c.id === e.target.value);
                if (reply) setBody((current) => current + fillPlaceholders(reply.body, placeholders));
              }}
            >
              <option value="">{copy.ticket.canned}</option>
              {canned.data.map((c) => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
          )}
        </div>
      )}
      <label className="composer__label" htmlFor={`composer-${ticketId}`}>{note ? copy.ticket.note : copy.ticket.reply}</label>
      <textarea
        id={`composer-${ticketId}`}
        ref={ref}
        className="composer__input"
        rows={4}
        value={body}
        placeholder={note ? copy.ticket.notePlaceholder : staff ? copy.ticket.replyPlaceholder : copy.portal.replyPlaceholder}
        onChange={(e) => {
          setBody(e.target.value);
          if (staff && Date.now() - lastTyping > TYPING_THROTTLE_MS) {
            sendTyping(ticketId);
            setLastTyping(Date.now());
          }
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) void submit(e);
        }}
      />
      <div className="composer__actions">
        <label className="composer__attach">
          {copy.ticket.attach}
          <input type="file" multiple className="composer__file" onChange={(e) => pickFiles(e.target.files)} />
        </label>
        {files.length > 0 && <span className="composer__files">{files.map((f) => f.name).join(', ')}</span>}
        <span className="composer__spacer" />
        {staff && !note && (
          <select
            className="composer__status"
            aria-label={copy.ticket.sendAs}
            value={statusAfter}
            onChange={(e) => setStatusAfter(e.target.value as TicketStatus)}
          >
            {STATUS_AFTER.map((s) => (
              <option key={s} value={s}>{`${copy.ticket.sendAs}: ${copy.status[s]}`}</option>
            ))}
          </select>
        )}
        <Button type="submit" variant="primary" loading={send.isPending} disabled={!body.trim()}>
          {copy.ticket.send}
        </Button>
      </div>
    </form>
  );
});
