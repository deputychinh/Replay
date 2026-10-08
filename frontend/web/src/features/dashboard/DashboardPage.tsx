import { Role, TicketStatus } from '@relay/api-client';
import { useAuth } from '../../app/auth';
import { useState } from 'react';
import { Button } from '../../components/button/Button';
import { ErrorState, Loading } from '../../components/empty-state/EmptyState';
import { TextField } from '../../components/field/Field';
import { useToast } from '../../components/toast/Toast';
import { copy } from '../../lib/copy';
import { formatDuration, formatNumber } from '../../lib/format';
import { useDashboard, useExport, useStartExport } from '../../queries/workspace';
import './dashboard.css';

const CHART_HEIGHT = 120;

function VolumeChart({ points }: { points: { day: string; count: number }[] }) {
  const max = Math.max(1, ...points.map((p) => p.count));
  const barWidth = 100 / points.length;
  return (
    <svg className="dashboard__chart" viewBox={`0 0 100 ${CHART_HEIGHT}`} preserveAspectRatio="none" role="img"
      aria-label={points.map((p) => `${p.day}: ${p.count}`).join(', ')}>
      {points.map((p, i) => {
        const height = (p.count / max) * (CHART_HEIGHT - 4);
        return <rect key={p.day} className="dashboard__bar" x={i * barWidth + barWidth * 0.15} y={CHART_HEIGHT - height}
          width={barWidth * 0.7} height={height} rx="0.6"><title>{`${p.day}: ${p.count}`}</title></rect>;
      })}
    </svg>
  );
}

function Exporter() {
  const today = new Date().toISOString().slice(0, 10);
  const monthAgo = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10);
  const [range, setRange] = useState({ from_date: monthAgo, to_date: today });
  const [exportId, setExportId] = useState<string | null>(null);
  const start = useStartExport();
  const job = useExport(exportId);
  const toast = useToast();
  return (
    <section className="dashboard__card dashboard__card--wide">
      <h2 className="dashboard__heading">{copy.dashboard.exportRange}</h2>
      <div className="dashboard__export">
        <TextField label="From" type="date" value={range.from_date} onChange={(e) => setRange({ ...range, from_date: e.target.value })} />
        <TextField label="To" type="date" value={range.to_date} onChange={(e) => setRange({ ...range, to_date: e.target.value })} />
        <Button variant="primary" loading={start.isPending}
          onClick={() => start.mutate(range, { onSuccess: (r) => setExportId(r.id), onError: (e) => toast(e.message, 'error') })}>
          {copy.dashboard.exportStart}
        </Button>
        {job.data?.status === 'ready' && job.data.download_url ? (
          <a className="dashboard__download" href={job.data.download_url}>{copy.dashboard.exportReady} ({job.data.row_count} rows)</a>
        ) : exportId ? <span className="dashboard__muted">{copy.dashboard.exportRunning}</span> : null}
      </div>
    </section>
  );
}

export function DashboardPage() {
  const dash = useDashboard();
  const { session } = useAuth();
  const manager = session?.user.role === Role.OWNER || session?.user.role === Role.ADMIN;
  if (dash.isPending) return <Loading />;
  if (dash.isError) return <ErrorState error={dash.error} onRetry={() => void dash.refetch()} />;
  const d = dash.data;
  const maxLoad = Math.max(1, ...d.agent_load.map((a) => a.open));

  return (
    <div className="dashboard">
      <h1 className="dashboard__title">{copy.dashboard.title}</h1>
      <div className="dashboard__kpis">
        <article className="dashboard__kpi">
          <h2 className="dashboard__label">{copy.dashboard.open}</h2>
          <p className="dashboard__value">{formatNumber(d.open_total)}</p>
        </article>
        <article className="dashboard__kpi dashboard__kpi--alert">
          <h2 className="dashboard__label">{copy.dashboard.breached}</h2>
          <p className="dashboard__value">{formatNumber(d.breached_open)}</p>
        </article>
        <article className="dashboard__kpi">
          <h2 className="dashboard__label">{copy.dashboard.firstResponse}</h2>
          <p className="dashboard__value">{d.first_response_p50_minutes != null ? formatDuration(d.first_response_p50_minutes) : '—'}</p>
          <p className="dashboard__muted">
            {copy.dashboard.firstResponseP90} {d.first_response_p90_minutes != null ? formatDuration(d.first_response_p90_minutes) : '—'} · {copy.dashboard.window(d.window_days)}
          </p>
        </article>
        <article className="dashboard__kpi">
          <h2 className="dashboard__label">{copy.dashboard.attainment}</h2>
          <p className="dashboard__value">{d.sla_attainment_percent != null ? `${d.sla_attainment_percent}%` : '—'}</p>
          <p className="dashboard__muted">{copy.dashboard.window(d.window_days)}</p>
        </article>
      </div>
      <div className="dashboard__grid">
        <section className="dashboard__card">
          <h2 className="dashboard__heading">{copy.dashboard.volume}</h2>
          <VolumeChart points={d.volume} />
        </section>
        <section className="dashboard__card">
          <h2 className="dashboard__heading">{copy.dashboard.byStatus}</h2>
          <ul className="dashboard__bars" role="list">
            {Object.values(TicketStatus).filter((s) => s in d.open_by_status).map((s) => (
              <li key={s} className="dashboard__row"><span>{copy.status[s]}</span><strong>{d.open_by_status[s]}</strong></li>
            ))}
          </ul>
        </section>
        <section className="dashboard__card">
          <h2 className="dashboard__heading">{copy.dashboard.load}</h2>
          <ul className="dashboard__bars" role="list">
            {d.agent_load.map((a) => (
              <li key={a.user_id} className="dashboard__row">
                <span>{a.full_name}</span>
                <meter className="dashboard__meter" min={0} max={maxLoad} value={a.open} aria-label={`${a.full_name}: ${a.open}`} />
                <strong>{a.open}</strong>
              </li>
            ))}
          </ul>
        </section>
        {manager && <Exporter />}
      </div>
    </div>
  );
}
