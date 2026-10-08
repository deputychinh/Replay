import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { copy } from '../../lib/copy';
import { formatRelative } from '../../lib/format';
import { useMarkNotificationsRead, useNotifications } from '../../queries/workspace';
import './notifications.css';

export function Notifications() {
  const { data } = useNotifications();
  const markRead = useMarkNotificationsRead();
  const [open, setOpen] = useState(false);
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!panel.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [open]);

  const unread = data?.unread ?? 0;
  return (
    <div className="notifications" ref={panel}>
      <button type="button" className="notifications__toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
        {copy.nav.notifications}
        {unread > 0 && <span className="notifications__count">{unread}</span>}
      </button>
      {open && (
        <div className="notifications__panel" role="dialog" aria-label={copy.nav.notifications}>
          <div className="notifications__header">
            <strong>{copy.nav.notifications}</strong>
            {unread > 0 && (
              <button type="button" className="notifications__read" onClick={() => markRead.mutate()}>
                {copy.nav.markAllRead}
              </button>
            )}
          </div>
          {data?.items.length ? (
            <ul className="notifications__list" role="list">
              {data.items.map((n) => (
                <li key={n.id} className={`notifications__item${n.read_at ? '' : ' notifications__item--unread'}`}>
                  {n.ticket_id ? (
                    <Link className="notifications__link" to={`/console/inbox/all/${n.ticket_id}`} onClick={() => setOpen(false)}>
                      {n.message}
                    </Link>
                  ) : (
                    <span>{n.message}</span>
                  )}
                  <time className="notifications__time" dateTime={n.created_at}>{formatRelative(n.created_at)}</time>
                </li>
              ))}
            </ul>
          ) : (
            <p className="notifications__empty">{copy.nav.noNotifications}</p>
          )}
        </div>
      )}
    </div>
  );
}
