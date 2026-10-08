# ADR-0004: Slow work goes to SQS; side effects run after commit; jobs are idempotent

**Status:** accepted · 2026-10-08

## Context
Sending email, assigning tickets, scanning SLAs and exporting CSV must not slow down requests. They must also not act on data that was rolled back, and they must not run twice.

## Decision
- The Unit of Work collects "after commit" actions (publish a real-time event, enqueue a job) and runs them only after a successful commit.
- Jobs go to SQS, with a dead-letter queue after 5 receives. The worker receives a job, inserts its idempotency key into `processed_jobs` in the same transaction as the job's effects, runs the handler, commits, and then deletes the message.
- Schedules (SLA scan every minute, auto-close hourly) come from EventBridge in AWS and from `python -m app.worker --schedule` locally. The key includes the tick time, so a duplicate delivery is skipped.
- SLA scan rows are locked with `FOR UPDATE SKIP LOCKED`, so two workers never alert twice.

## Consequences
- At-least-once delivery from SQS becomes effectively exactly-once for each job's database effects.
- Email sending can still repeat if the SMTP/SES call succeeds and the commit then fails. That is accepted for notifications.
