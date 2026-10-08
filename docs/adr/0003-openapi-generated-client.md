# ADR-0003: The Python enums and schemas are the single source; TypeScript is generated

**Status:** accepted · 2026-10-08

## Context
Ticket statuses, priorities, event names and every request and response shape are used by the API and by the web app. Writing them twice means they drift apart.

## Decision
- Every enum lives in `backend/app/common/enums.py`, every limit in `constants.py`, and every API shape in Pydantic schemas.
- `make gen-client` exports the OpenAPI document. `openapi-typescript` turns it into types, and a small script turns each enum schema into an `as const` object in `frontend/packages/api-client`.
- CI regenerates both and fails on any diff.

## Consequences
- Renaming a status breaks the TypeScript build at compile time, not in production.
- A few UI-only mirrors (the upload size and type limits, the SLA warning window) are kept next to a comment that names their backend constant.
