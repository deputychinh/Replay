// Session: the access token lives in memory only; the refresh token is an httpOnly cookie
// the browser sends to /api/v1/auth. On load we try one refresh to restore the session.
import { api, configureSession, unwrap, type Schemas } from '@relay/api-client';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

type Session = Schemas['SessionOut'];

interface AuthState {
  session: Session | null;
  ready: boolean;
  signIn: (organization: string, email: string, password: string) => Promise<Session>;
  register: (body: Schemas['RegisterIn']) => Promise<Session>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const token = useRef<string | null>(null);
  const refreshing = useRef<Promise<string | null> | null>(null);

  const apply = useCallback((next: Session | null) => {
    token.current = next?.access_token ?? null;
    setSession(next);
  }, []);

  const refresh = useCallback(async () => {
    // One refresh at a time, shared by every request that got a 401.
    refreshing.current ??= api
      .POST('/api/v1/auth/refresh')
      .then((r) => {
        const next = r.response.ok ? (r.data ?? null) : null;
        apply(next);
        return next?.access_token ?? null;
      })
      .finally(() => {
        refreshing.current = null;
      });
    return refreshing.current;
  }, [apply]);

  useEffect(() => {
    configureSession({ getToken: () => token.current, refresh });
    void refresh().finally(() => setReady(true));
  }, [refresh]);

  const value = useMemo<AuthState>(
    () => ({
      session,
      ready,
      async signIn(organization, email, password) {
        const next = unwrap(await api.POST('/api/v1/auth/login', { body: { organization, email, password } }));
        apply(next);
        return next;
      },
      async register(body) {
        const next = unwrap(await api.POST('/api/v1/auth/register', { body }));
        apply(next);
        return next;
      },
      async signOut() {
        await api.POST('/api/v1/auth/logout');
        apply(null);
      },
    }),
    [session, ready, apply],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}

export function accessToken(session: Session | null): string | null {
  return session?.access_token ?? null;
}
