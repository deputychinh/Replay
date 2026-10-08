# ADR-0002: One React app with two areas, console and portal

**Status:** accepted · 2026-10-08

## Context
The plan first had a React console for agents and a Vue portal for customers. The decision on 2026-10-08 was React only.

## Decision
One Vite + React 19 app with two route trees:
- `/console/*`: staff only (guarded), dark sidebar, virtualised inbox, live updates.
- `/portal/:org/*`: customers only (guarded), light and simple.

Both areas share the design tokens, the BEM component blocks and the generated API client. Dashboard, settings and the whole portal are lazy-loaded, so customers never download the console.

## Consequences
- One build, one deploy, one CloudFront distribution.
- Role checks happen twice: the router guards are for user experience, and the API enforces the real rule.
