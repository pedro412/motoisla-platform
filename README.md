# Moto Isla

Monorepo for Moto Isla — a motorcycle parts and accessories store management system.

## Structure

```
apps/
  client/   → Next.js frontend (App Router, MUI, TanStack Query)
  server/   → Django backend API (DRF, PostgreSQL)
```

## Request flow

```
Browser → client (Next.js proxy) → server (Django API)
```

All browser API calls go through the Next.js proxy at `/api/proxy/[...path]` — never directly to Django.

## Development

```bash
# Frontend
make dev-client          # or: cd apps/client && pnpm dev

# Backend
make dev-server          # or: cd apps/server && docker compose up --build
```

## Testing

```bash
make test-client         # Vitest unit tests
make test-server         # Django tests (via Docker)
make lint-client         # ESLint
```

## Releasing

1. Go to Actions → **Release** workflow
2. Choose bump type (patch/minor/major) and optionally dry-run
3. The workflow creates a tag → triggers **Deploy Production**
4. Deploy Production: server deploys first (Railway), then client (Vercel)

## Detailed docs

- **Client**: [`apps/client/CLAUDE.md`](apps/client/CLAUDE.md)
- **Server**: [`apps/server/CLAUDE.md`](apps/server/CLAUDE.md)
