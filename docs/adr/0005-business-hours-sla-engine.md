# ADR-0005: SLA maths as pure functions on business hours

**Status:** accepted · 2026-10-08

## Context
SLA targets are measured in business hours of the support team (for example New York 09:00–17:00 on weekdays, excluding holidays). The clock pauses while the team waits on the customer. Time zones and DST changes make this easy to get wrong.

## Decision
- `app/sla/clock.py` has two pure functions: `due_at(start, minutes, calendar)` and `business_minutes_between(start, end, calendar)`. They work on aware datetimes, convert through UTC, and use only `zoneinfo`.
- Pausing stores the business minutes left. Resuming computes a new due time from them.
- Postgres keeps a generated column `sla_due_at` (the next deadline). The "Breaching soon" view and the SLA sort use it through one index.
- Table-driven tests cover overnight, weekends, holidays, the DST change and other time zones.

## Consequences
- Changing business hours applies to new or resumed clocks, not to deadlines already computed. This is documented in the UI.
