import { MessageKind } from '@relay/api-client';
import { Avatar } from '../../components/avatar/Avatar';
import { copy } from '../../lib/copy';
import { formatDateTime } from '../../lib/format';
import type { Message } from '../../queries/tickets';
import { downloadUrl } from '../../queries/workspace';
import './thread.css';

async function openAttachment(id: string) {
  window.open(await downloadUrl(id), '_blank', 'noopener');
}

/** The conversation. `perspective` decides which side is "us" in the bubbles. */
export function Thread({ messages, perspective }: { messages: Message[]; perspective: 'staff' | 'customer' }) {
  return (
    <ol className="thread" role="list">
      {messages.map((m) => {
        const ours = perspective === 'staff' ? m.author_is_staff : !m.author_is_staff;
        const note = m.kind === MessageKind.INTERNAL_NOTE;
        const classes = ['thread__message', ours && 'thread__message--ours', note && 'thread__message--note'].filter(Boolean);
        return (
          <li key={m.id} className={classes.join(' ')}>
            <Avatar name={m.author.full_name} staff={m.author_is_staff} />
            <div className="thread__bubble">
              <div className="thread__head">
                <span className="thread__author">{m.author.full_name}</span>
                {note && <span className="thread__note-label">{copy.ticket.internal}</span>}
                <time className="thread__time" dateTime={m.created_at}>{formatDateTime(m.created_at)}</time>
              </div>
              <p className="thread__body">{m.body}</p>
              {m.attachments.length > 0 && (
                <ul className="thread__files" role="list">
                  {m.attachments.map((file) => (
                    <li key={file.id}>
                      <button type="button" className="thread__file" onClick={() => void openAttachment(file.id)}>
                        {file.filename} · {Math.max(1, Math.round(file.size_bytes / 1024))} KB
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
