import { Role } from '@relay/api-client';
import { Navigate, NavLink, Outlet, useNavigate, useParams } from 'react-router';
import { useAuth } from '../../app/auth';
import { Loading } from '../../components/empty-state/EmptyState';
import { copy } from '../../lib/copy';
import './portal.css';

export function PortalShell() {
  const { org = '' } = useParams();
  const { session, ready, signOut } = useAuth();
  const navigate = useNavigate();
  if (!ready) return <Loading />;
  if (!session || session.user.role !== Role.CUSTOMER || session.organization_slug !== org) {
    return <Navigate to={`/portal/${org}/sign-in`} replace />;
  }
  return (
    <div className="portal">
      <header className="portal__bar">
        <span className="portal__brand">{copy.auth.portalTitle(org)}</span>
        <nav className="portal__nav" aria-label="Portal">
          <NavLink end to={`/portal/${org}`} className="portal__link">{copy.portal.myTickets}</NavLink>
          <NavLink to={`/portal/${org}/new`} className="portal__link">{copy.portal.newTicket}</NavLink>
        </nav>
        <button type="button" className="portal__signout" onClick={() => void signOut().then(() => navigate(`/portal/${org}/sign-in`))}>
          {copy.common.signOut}
        </button>
      </header>
      <main className="portal__main" id="main"><Outlet /></main>
    </div>
  );
}
