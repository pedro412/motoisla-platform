# MotoIsla Client

Base inicial del dashboard administrativo en Next.js para consumir un backend existente.

## Stack

- Next.js (App Router) + TypeScript
- Material UI (tema oscuro por defecto)
- TanStack Query
- Vitest + Testing Library
- Playwright (smoke e2e)
- ESLint + Prettier

## Scripts

- `pnpm dev`: servidor local
- `pnpm build`: build de producción
- `pnpm start`: servidor de producción
- `pnpm lint`: lint
- `pnpm typecheck`: chequeo de tipos
- `pnpm test`: tests unit/integration
- `pnpm test:e2e`: tests e2e smoke

## Estructura

- `src/app/(auth)`: rutas públicas de autenticación (`/login`, `/recuperar-cuenta`)
- `src/app/(admin)`: rutas internas del dashboard (`/dashboard`, `/productos`, `/ventas`)
- `src/components/layout`: shell principal (sidebar, topbar, app shell)
- `src/lib/api`: `http-client`, errores y query client
- `src/lib/auth`: contratos de autorización para futura implementación
- `src/modules`: servicios y lógica por módulo
- `src/theme`: configuración del tema MUI

## Permisos (preparado para backend)

La lógica de permisos no está activa todavía, pero ya se dejaron:

- `requiredPermissions` en items de menú
- `AuthSession` placeholder
- `PermissionEvaluator` como punto único para inyectar reglas de acceso

## Próximos pasos

1. Integrar autenticación real con backend
2. Activar filtros de menú/rutas por permisos
3. Añadir toggle dark/light persistido
