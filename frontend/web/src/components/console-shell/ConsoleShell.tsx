import { TicketView } from '@relay/api-client';
import { NavLink, Outlet, useNavigate } from 'react-router';
import { useAuth } from '../../app/auth';
import { copy } from '../../lib/copy';
import { useRealtime, type LiveEvent } from '../../lib/realtime';
import { Avatar } from '../avatar/Avatar';
import { Notifications } from '../notifications/Notifications';
import { useToast } from '../toast/Toast';
import './console-shell.css';

const VIEWS = [TicketView.MINE, TicketView.UNASSIGNED, TicketView.BREACHING_SOON, TicketView.ALL];

export function ConsoleShell() {
  const { session, signOut } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const live = useRealtime(session?.access_token ?? null, (event: LiveEvent) => {
    const label = copy.liveEvents[event.event as keyof typeof copy.liveEvents];
    if (label) toast(label, event.event === 'ticket.sla_breached' ? 'error' : 'info');
  });

  return (
    <div className="console-shell">
      <a className="console-shell__skip" href="#main">Skip to content</a>
      <aside className="console-shell__sidebar">
        <div className="console-shell__brand">
          <span className="console-shell__logo" aria-hidden="true">R</span>
          {copy.brand}
          <span className={`console-shell__live${live ? ' console-shell__live--on' : ''}`} title={live ? copy.inbox.live : copy.inbox.offline}>
            {live ? copy.inbox.live : copy.inbox.offline}
          </span>
        </div>
        <Notifications />
        <nav className="console-shell__nav" aria-label="Main">
          <p className="console-shell__heading">{copy.nav.inbox}</p>
          {VIEWS.map((view) => (
            <NavLink key={view} to={`/console/inbox/${view}`} className="console-shell__link">
              {copy.views[view]}
            </NavLink>
          ))}
          <p className="console-shell__heading">Team</p>
          <NavLink to="/console/dashboard" className="console-shell__link">{copy.nav.dashboard}</NavLink>
          <NavLink to="/console/settings" className="console-shell__link">{copy.nav.settings}</NavLink>
          <a href={`/portal/${session?.organization_slug ?? ''}`} className="console-shell__link" target="_blank" rel="noreferrer">
            {copy.nav.portal}
          </a>
        </nav>
        {session && (
          <div className="console-shell__user">
            <Avatar name={session.user.full_name} staff />
            <span className="console-shell__who">
              <span className="console-shell__name">{session.user.full_name}</span>
              <span className="console-shell__role">{session.user.role}</span>
            </span>
            <button
              type="button"
              className="console-shell__signout"
              onClick={() => void signOut().then(() => navigate('/login'))}
            >
              {copy.common.signOut}
            </button>
          </div>
        )}
      </aside>
      <main className="console-shell__main" id="main">
        <Outlet />
      </main>
    </div>
  );
}
