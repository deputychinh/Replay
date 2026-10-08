// NFR-01: list/detail p95 < 200 ms at 200 requests per second, with 1,000,000 tickets in the table.
//   make seed-large && make api   (or the API with several uvicorn workers), then:  k6 run loadtest/tickets.js
import http from 'k6/http';
import { check } from 'k6';

const API = __ENV.API ?? 'http://localhost:8030/api/v1';
const VIEWS = ['all', 'mine', 'unassigned', 'breaching_soon'];
const SORTS = ['newest', 'priority', 'sla_due'];

export const options = {
  scenarios: {
    agents: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE ?? 200),
      timeUnit: '1s',
      duration: __ENV.DURATION ?? '60s',
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
  thresholds: {
    'http_req_duration{kind:list}': ['p(95)<200'],
    'http_req_duration{kind:detail}': ['p(95)<200'],
    http_req_failed: ['rate<0.01'],
  },
};

export function setup() {
  const login = http.post(`${API}/auth/login`, JSON.stringify({ organization: 'acme', email: 'agent@acme.demo', password: 'Demo@1234' }), {
    headers: { 'Content-Type': 'application/json' },
  });
  const token = login.json('access_token');
  const headers = { Authorization: `Bearer ${token}` };
  const first = http.get(`${API}/tickets?view=all&limit=100`, { headers }).json('items');
  return { headers, ids: first.map((t) => t.id) };
}

export default function ({ headers, ids }) {
  const roll = Math.random();
  if (roll < 0.6) {
    const view = VIEWS[Math.floor(Math.random() * VIEWS.length)];
    const sort = SORTS[Math.floor(Math.random() * SORTS.length)];
    const res = http.get(`${API}/tickets?view=${view}&sort=${sort}&limit=25`, { headers, tags: { kind: 'list' } });
    check(res, { 'list 200': (r) => r.status === 200 });
  } else {
    const id = ids[Math.floor(Math.random() * ids.length)];
    const res = http.get(roll < 0.85 ? `${API}/tickets/${id}` : `${API}/tickets/${id}/messages`, { headers, tags: { kind: 'detail' } });
    check(res, { 'detail 200': (r) => r.status === 200 });
  }
}
