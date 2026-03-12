# Next Steps (Ordered Backlog)

Este backlog mantiene el orden del plan original y deja tareas ejecutables para siguientes agentes.

## Prioridad 1 — Fase 7 (Auditoría + Métricas) cerrada
1. ✅ Métricas ampliadas (`/api/v1/metrics/`) por rango/productos/pagos.
2. ✅ Reporte admin (`/api/v1/reports/sales/`) por día/cajero.
3. ✅ Integración de gastos en reportes (`expenses_summary`, `net_sales_after_expenses`).
4. ✅ Auditoría ampliada (catálogo, inventario, inversionistas y gastos).
5. ✅ Cobertura de tests de regresión para métricas/reportes y gastos.

## Prioridad 2 — Fase 8 (Hardening) cerrada
1. ✅ Security checklist:
- checklist documentado en `docs/SECURITY_CHECKLIST.md`
- settings de prod endurecidos (`DEBUG`, hosts, secrets, CSRF/CORS, SSL/cookies/HSTS)
2. ✅ Performance:
- revisión aplicada de `select_related/prefetch_related` y filtros tempranos
- índices agregados en módulos críticos (sales/audit/ledger/layaway)
3. ✅ Operación:
- colección de requests QA creada (`docs/API_QA_COLLECTION.http`)
- runbook de incidencias documentado (`docs/RUNBOOK.md`)
4. ✅ Calidad:
- DoD v1 documentada (`docs/DOD_V1.md`)
5. Seguimiento operativo post-cierre:
- validar configuración CSRF/CORS con dominios reales de frontend en staging/prod
- capturar baseline de performance con datos reales (latencia y query plans)

## Prioridad 3 — Módulo de gastos (v1) cerrado
1. ✅ API de gastos recurrentes y variables.
2. ✅ Integración en reportería gerencial usando solo gastos `PAID`.
3. ✅ Tests de agregación por categoría, periodo y generación mensual.

## Prioridad 4 — Reportería financiera (siguiente iteración)
1. Consolidar reportería exacta de consumo por asignación/venta para inversionistas (fase 2).
2. Evaluar tabla explícita de consumos por venta para eliminar inferencias en métricas.
3. ✅ Exponer filtros de período y totales agregados en `GET /investors/{id}/ledger/` (`entry_type`, `date_from`, `date_to`, `totals`).

## Prioridad 5 — Soporte frontend catalog-only
1. ✅ Endpoint de catálogo público readonly (`/api/v1/public/catalog/`, `/api/v1/public/catalog/{sku}/`).
2. ✅ Rate limiting/caching básico para consulta pública.
3. Siguiente iteración:
- acordar contrato final con frontend web (campos/orden/filtros adicionales)
- evaluar cache externa (Redis/CDN) para tráfico alto

## Prioridad 6 — Seguimiento operativo
1. ✅ Validar CSRF/CORS con dominios reales en staging/prod — CORS methods/headers restringidos.
2. Capturar baseline de performance (latencia p95 + query plans) con tráfico real.
3. Endurecer concurrencia en compras de inversionistas para evitar sobreasignación bajo requests simultáneos.
4. ✅ Rate limiting global (anon 60/min, user 300/min) + JWT refresh token rotation con blacklist.
5. ✅ Admin path ofuscado (`/backoffice-mi/`).
6. Evaluar `django-axes` para lockout de login si se expone a internet público sin VPN.

## Prioridad 7 — Ventas (siguiente iteración UX/operación) ✅
1. ✅ Filtros server-side para `GET /api/v1/sales/` — `status`, `cashier`, `date_from`, `date_to`. UI en `/ventas` con patrón draft/applied.
2. ✅ Endpoint atómico `POST /api/v1/sales/create-and-confirm/` — crea y confirma en una sola transacción. POS actualizado para usarlo.
3. ✅ Exponer reportería de comisiones de tarjeta para utilidad operativa y conciliación — `card_instrument` en Payment/CardCommissionPlan/LayawayPayment, desglose `card_instruments` en métricas/reportes.

## Prioridad 8 — Inversionistas (siguiente iteración operativa) ✅
1. ✅ Reinversión de utilidades — `POST /investors/{id}/reinvest/` + botón "Reinvertir utilidad" en UI (bloqueado cuando profit ≤ 0).
2. ✅ Filtros de ledger — `entry_type`, `date_from`, `date_to` + totales de período en UI.
3. Evaluar locking explícito por producto/asignación para compras concurrentes.

## Prioridad 9 — Integridad del ledger: inmutabilidad y reconciliación ✅

> Objetivo: que el ledger sea la única fuente de verdad. Cualquier balance o cantidad derivada
> siempre debe poder recalcularse desde cero sumando entradas del ledger. Sin campos cacheados
> que puedan desincronizarse silenciosamente.

1. ✅ **Atomicidad en `profitability.py`**: `apply_sale_profitability` y `revert_sale_profitability` decoradas con `@transaction.atomic` — savepoint automático cuando se llaman desde `confirm`/`void`; protección propia si se llaman en solitario.
2. ✅ **Inmutabilidad de `LedgerEntry`**: `save()` lanza `ValidationError` si `_state.adding` es `False`. Ningún código puede editar entradas existentes; solo se permiten entradas compensatorias.
3. ✅ **Comando `reconcile_ledger`** (`python manage.py reconcile_ledger`): verifica balances del ledger por inversionista y `qty_sold` de cada `InvestorAssignment` contra `SaleLineProfitability`. Solo lectura, exit code 0 = OK / 1 = mismatches. Usable en CI/monitoring/cron.
4. ✅ **Unit tests de lógica pura** (`ProfitabilityUnitTests`): `allocate_proportionally`, `_build_line_chunks` (STORE, INVESTOR, mixto, FIFO multi-inversor), split 50/50, cero profit.
5. ✅ **Chaos tests** (`ProfitabilityChaosTests`): rollback de apply/revert en fallo DB, validación de inmutabilidad de ledger entry.

## Prioridad 10 — Cobertura de tests: lógica financiera crítica ✅

1. ✅ Unit tests de `allocate_proportionally` y `_build_line_chunks` en `ProfitabilityUnitTests`.
2. ✅ Casos borde cubiertos: chunks STORE + múltiples inversionistas FIFO, venta con profit cero, rollback parcial.
3. ✅ Chaos tests de `apply_sale_profitability` y `revert_sale_profitability`.
4. ✅ Test de inmutabilidad de `LedgerEntry`.
5. ✅ Integration test de ciclo completo confirmar→anular ya existía; chaos tests validan el rollback explícito.

## Prioridad 11 — User Management & Password Reset ✅
1. ✅ `User.email` unique constraint + data migration for existing users.
2. ✅ Custom `UserManager` auto-generates placeholder email when blank (backwards compat for tests).
3. ✅ `UserViewSet` — full CRUD at `/users/` with `users.manage` capability (ADMIN only). DELETE returns 405; use `is_active` toggle.
4. ✅ Serializers: `UserCreateSerializer` (sets `username=email`, Group assignment, optional Investor linking), `UserUpdateSerializer`, `UserListSerializer`.
5. ✅ `PasswordResetRequestView` at `/auth/password-reset/` — AllowAny, throttled 5/hour, generic response (OWASP).
6. ✅ `PasswordResetConfirmView` at `/auth/password-reset-confirm/` — validates token + password against Django validators.
7. ✅ Email: console backend by default, Gmail SMTP ready. HTML template with dark theme. `PASSWORD_RESET_TIMEOUT=3600`.
8. ✅ Audit trail on `user.create`, `user.update`, `password_reset.request`, `password_reset.confirm`.

## Prioridad 12 — Clientes / lealtad (backlog)
1. Diseñar programa de lealtad o descuentos basado en historial de compras del `Customer`.
2. Definir reglas de elegibilidad y trazabilidad para promociones por recurrencia.

## Notas para agentes
- No romper contratos actuales de API (`code/detail/fields`, paginación DRF).
- Mantener reglas de negocio ya cerradas en fases 3-6.
- Antes de cambios grandes, actualizar `docs/PLAN_STATUS.md` y este backlog.
- Recordar que cambios de UI del cliente (breadcrumbs, headers de detalle, etiquetas visuales) no requieren cambios de contrato salvo que se modifique el payload.
