# Moto Isla — Monorepo Agent Context

## Structure

```
motoisla-platform/
├── apps/
│   ├── client/    ← Next.js frontend (see apps/client/CLAUDE.md)
│   └── server/    ← Django backend API (see apps/server/CLAUDE.md)
├── .github/workflows/
│   ├── ci-client.yml     ← lint + typecheck + test (path: apps/client/**)
│   ├── ci-server.yml     ← test + deploy checks (path: apps/server/**)
│   ├── deploy-prod.yml   ← tag v* → deploy server then client
│   └── release.yml       ← workflow_dispatch: bump version, create tag
└── Makefile              ← convenience commands
```

## Request flow

```
Browser component
  → httpClient (apps/client/src/lib/api/http-client.ts)
    → /api/proxy/[...path] (Next.js route handler)
      → Django backend /api/v1/...
```

## Development commands

```bash
make dev-client       # Next.js dev server (localhost:3000)
make dev-server       # Docker compose up (localhost:8000)
make test-client      # Vitest
make test-server      # Django test (via Docker)
make lint-client      # ESLint
```

## CI/CD

- **CI**: path-filtered — changes in `apps/client/` trigger `ci-client.yml`, changes in `apps/server/` trigger `ci-server.yml`
- **Deploy**: `release.yml` (manual) → creates tag → `deploy-prod.yml` detects which app changed → deploys server first (Railway), then client (Vercel)
- No cross-repo PAT needed — everything is in one repo

## Detailed context

- **Client**: `apps/client/CLAUDE.md` — full architecture, conventions, routes
- **Server**: `apps/server/CLAUDE.md` or `apps/server/docs/AGENT_CONTEXT.md` — API endpoints, business rules
