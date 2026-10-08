import { Role } from '@relay/api-client';
import { lazy, Suspense, type ReactNode } from 'react';
import { createBrowserRouter, Navigate, Outlet } from 'react-router';
import { ConsoleShell } from '../components/console-shell/ConsoleShell';
import { EmptyState, Loading } from '../components/empty-state/EmptyState';
import { LoginPage } from '../features/auth/LoginPage';
import { InboxPage } from '../features/inbox/InboxPage';
import { copy } from '../lib/copy';
import { useAuth } from './auth';

// Code-split: the inbox loads first; dashboard, settings and the whole portal load on demand.
const named = <K extends string>(load: () => Promise<Record<K, React.ComponentType<never>>>, key: K) =>
  lazy(async () => ({ default: (await load())[key] as React.ComponentType<Record<string, unknown>> }));
const DashboardPage = named(() => import('../features/dashboard/DashboardPage'), 'DashboardPage');
const SettingsPage = named(() => import('../features/settings/SettingsPage'), 'SettingsPage');
const PortalShell = named(() => import('../features/portal/PortalShell'), 'PortalShell');
const PortalAuthPage = named(() => import('../features/portal/PortalAuthPage'), 'PortalAuthPage');
const MyTicketsPage = named(() => import('../features/portal/MyTicketsPage'), 'MyTicketsPage');
const NewTicketPage = named(() => import('../features/portal/NewTicketPage'), 'NewTicketPage');
const PortalTicketPage = named(() => import('../features/portal/PortalTicketPage'), 'PortalTicketPage');

const page = (node: ReactNode) => <Suspense fallback={<Loading />}>{node}</Suspense>;

/** The console is for staff only; customers belong in the portal. */
function RequireStaff() {
  const { session, ready } = useAuth();
  if (!ready) return <Loading />;
  if (!session) return <Navigate to="/login" replace />;
  if (session.user.role === Role.CUSTOMER) return <Navigate to={`/portal/${session.organization_slug}`} replace />;
  return <Outlet />;
}

export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/console/inbox/mine" replace /> },
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireStaff />,
    children: [
      {
        path: '/console',
        element: <ConsoleShell />,
        children: [
          { index: true, element: <Navigate to="inbox/mine" replace /> },
          { path: 'inbox/:view/:ticketId?', element: <InboxPage /> },
          { path: 'dashboard', element: page(<DashboardPage />) },
          { path: 'settings', element: page(<SettingsPage />) },
        ],
      },
    ],
  },
  { path: '/portal/:org/sign-in', element: page(<PortalAuthPage mode="sign-in" />) },
  { path: '/portal/:org/sign-up', element: page(<PortalAuthPage mode="sign-up" />) },
  {
    path: '/portal/:org',
    element: page(<PortalShell />),
    children: [
      { index: true, element: page(<MyTicketsPage />) },
      { path: 'new', element: page(<NewTicketPage />) },
      { path: 'tickets/:ticketId', element: page(<PortalTicketPage />) },
    ],
  },
  { path: '*', element: <EmptyState title={copy.errors.notFound} /> },
]);
