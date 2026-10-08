# ADR-0001: Layered FastAPI with tenant isolation by construction

**Status:** accepted · 2026-10-08

## Context
Relay serves many organisations from one database. One missing `WHERE org_id = …` would show one company's tickets to another company.

## Decision
- Layers: router → service → repository → model. Routers hold no rules, services never raise HTTP errors, and repositories hold all SQL.
- Every model with `org_id` is read through a `TenantRepository`. Its `scoped()` method always adds `WHERE org_id = :org_of_the_caller`, and the org comes from the JWT, never from the request body.
- A unit test fails if any table with `org_id` has no tenant repository. An integration test calls every ticket route as another organisation and expects 404.
- A cross-tenant id returns 404, not 403, so the response never confirms that the id exists.

## Consequences
- A new feature cannot read across tenants by accident, because there is no unscoped helper to call.
- System jobs that sweep all tenants (SLA scan, auto-close) loop over organisations explicitly, so the exception is visible.
