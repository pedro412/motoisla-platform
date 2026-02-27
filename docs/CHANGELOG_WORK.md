# Work Changelog

## 2026-02-27
- Integración del cliente con backend real vía BFF.
- Implementación de handlers auth y proxy autenticado.
- Reorganización de rutas a `(public)`, `(auth)`, `(private)`.
- Implementación de catálogo público, POS y reportes admin.
- Implementación de store de sesión con Zustand.
- Corrección de redirección raíz y rutas legacy (`/dashboard`, `/productos`, `/ventas`).
- Corrección de `proxy.ts` para Next 16.
- Validaciones ejecutadas: lint, typecheck, test, test:e2e.

## 2026-02-27 (Compras)
- Nueva pantalla `/purchases/imports` con selector proveedor/parser.
- Integración con `import-batches`: create, parse, edición de líneas y confirmación.
- Soporte de `public_price` editable con margen en vivo por línea.
- Placeholder de feature futuro para carga de imagen en tabla preview.

## 2026-02-27 (Compras v6)
- Migración a parse en cliente para parser MYESA (`src/modules/purchases/parsers/myesa.parser.ts`).
- Nuevo submit único de compra al endpoint backend `POST /import-batches/preview-confirm/`.
- Eliminación de roundtrip de parse para preview (respuesta inmediata en UI).
- Tests unitarios nuevos del parser MYESA con caso real y fallback de líneas inválidas.
