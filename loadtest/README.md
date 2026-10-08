Load test (NFR-01)

Goal: listing and opening tickets stays under 200 ms at the 95th percentile, at 200 requests per second, with 1,000,000 tickets in the table.

How to run:

    make up && make migrate && make seed-large
    cd backend && uv run uvicorn app.main:app --port 8030 --workers 4 --log-level warning
    k6 run loadtest/tickets.js                       # 200 req/s for 60 s
    k6 run -e RATE=800 -e DURATION=30s loadtest/tickets.js

The traffic mix is 60 % list requests (random view and sort) and 40 % ticket detail and messages requests, all as one agent.

Results (2026-10-08, MacBook Pro M-series, everything in Docker on the same laptop, 1,005,000 tickets):

| Run | Throughput | List p95 | Detail p95 | Errors |
|---|---|---|---|---|
| Before the list indexes | 83 req/s (could not keep 200) | 4.94 s | 3.54 s | 0 % |
| After, 200 req/s | 199 req/s | 7.9 ms | 6.0 ms | 0 % |
| After, 800 req/s | 794 req/s | 11.1 ms | 9.7 ms | 0 % |

What changed: every list was doing a parallel scan of the whole table (35 to 65 ms each, with all CPU cores busy), because no index matched its sort order. The fix:

- One index per list order: updated_at, priority, and a partial index for unassigned open tickets.
- A generated column, sla_due_at, holding the next SLA deadline. It has its own index, so the "Breaching soon" view and the SLA sort became index range scans instead of an OR across two columns.
- "Breaching soon" is always sorted by that deadline.

Keyset (cursor) pagination keeps page 1,000 as fast as page 1.
