// Typed API client (openapi-fetch) with the access token, one silent refresh on 401,
// and errors turned into ApiError with the server's code and request id.
import createClient, { type Middleware } from 'openapi-fetch';
import type { components, paths } from './schema';

export type Schemas = components['schemas'];

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: unknown,
    readonly requestId: string | null,
  ) {
    super(message);
  }
}

interface Session {
  getToken: () => string | null;
  /** Called once per 401; returns a new access token, or null when the session is over. */
  refresh: () => Promise<string | null>;
}

let session: Session = { getToken: () => null, refresh: async () => null };

export function configureSession(next: Session): void {
  session = next;
}

const REFRESH_PATH = '/api/v1/auth/refresh';
const retried = new WeakSet<Request>();

const auth: Middleware = {
  onRequest({ request }) {
    const token = session.getToken();
    if (token) request.headers.set('Authorization', `Bearer ${token}`);
    return request;
  },
  async onResponse({ request, response }) {
    if (response.status !== 401 || request.url.endsWith(REFRESH_PATH) || retried.has(request)) return response;
    const token = await session.refresh();
    if (!token) return response;
    const retry = new Request(request, { headers: new Headers(request.headers) });
    retry.headers.set('Authorization', `Bearer ${token}`);
    retried.add(retry);
    return fetch(retry);
  },
};

export const api = createClient<paths>({ baseUrl: '', credentials: 'include' });
api.use(auth);

/** Unwrap an openapi-fetch result: data, or throw ApiError. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || !result.response.ok) {
    const body = (result.error ?? {}) as { error?: Schemas['ApiErrorDetail'] };
    const e = body.error;
    throw new ApiError(
      result.response.status,
      e?.code ?? 'INTERNAL_ERROR',
      e?.message ?? 'Something went wrong. Please try again.',
      e?.details,
      e?.request_id ?? result.response.headers.get('X-Request-ID'),
    );
  }
  return result.data as T;
}
