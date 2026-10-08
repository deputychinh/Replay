import { ApiError } from '@relay/api-client';
import type { ReactNode } from 'react';
import { copy } from '../../lib/copy';
import { Button } from '../button/Button';
import './empty-state.css';

export function EmptyState({ title, hint, children }: { title: string; hint?: string; children?: ReactNode }) {
  return (
    <div className="empty-state">
      <p className="empty-state__title">{title}</p>
      {hint && <p className="empty-state__hint">{hint}</p>}
      {children}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const api = error instanceof ApiError ? error : null;
  return (
    <div className="empty-state empty-state--error" role="alert">
      <p className="empty-state__title">{api?.message ?? copy.errors.generic}</p>
      {api?.requestId && <p className="empty-state__hint">{copy.common.reference}: {api.requestId}</p>}
      {onRetry && <Button onClick={onRetry}>{copy.common.retry}</Button>}
    </div>
  );
}

export function Loading() {
  return (
    <div className="empty-state" aria-busy="true">
      <span className="empty-state__spinner" />
      <span className="empty-state__hint">{copy.common.loading}</span>
    </div>
  );
}
