# QA Checklist (Local)

## Auth
- [ ] Login válido crea sesión.
- [ ] Logout limpia sesión y bloquea rutas privadas.
- [ ] Refresh funciona cuando expira access token.

## Catalog
- [ ] `/catalog` carga lista pública.
- [ ] búsqueda por `q` devuelve resultados.
- [ ] `/catalog/{sku}` muestra detalle.

## POS
- [ ] create sale genera `DRAFT`.
- [ ] confirm cambia a `CONFIRMED`.
- [ ] void cambia a `VOID` según permisos/ventana.
- [ ] errores backend (`code/detail/fields`) se muestran correctamente.

## Reports
- [ ] `/admin/reports` responde con filtros de rango.
- [ ] muestra total sales, avg ticket y top products.
- [ ] muestra neto después de gastos.

## Purchases
- [ ] `/purchases/imports` carga proveedores y parsers.
- [ ] parse de factura MYESA genera preview editable.
- [ ] `precio_publico` y margen se actualizan en tiempo real.
- [ ] confirmación de compra devuelve `purchase_receipt_id`.
- [ ] stock incrementa después de confirmar.

## Guards
- [ ] usuario sin sesión no entra a `/pos` ni `/admin/*`.
- [ ] `CASHIER` no accede a `/admin/reports`.
