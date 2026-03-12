# R2 Production Checklist (Server)

Checklist para configurar Cloudflare R2 en staging/prod para el backend de media.

## 1) Infra recomendada
- Bucket separado por ambiente:
  - `motoisla-media-staging`
  - `motoisla-media-prod`
- URL publica estable por ambiente:
  - staging: `media-staging.tudominio.com`
  - prod: `media.tudominio.com`

## 2) Credenciales y permisos minimos
- Crear API token R2 con alcance al bucket correcto.
- Generar `R2_ACCESS_KEY_ID` y `R2_SECRET_ACCESS_KEY` por ambiente.
- No reutilizar llaves entre staging y prod.
- Rotar llaves periodicamente (ej. cada 90 dias).

## 3) Variables de entorno backend
Definir en el proveedor de deploy (Railway u otro):

```env
MEDIA_PROVIDER=R2
R2_ACCOUNT_ID=...
R2_BUCKET=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_PUBLIC_BASE_URL=https://media.tudominio.com
MEDIA_MAX_BYTES=8388608
MEDIA_MAX_DIMENSION=3000
MEDIA_ALLOWED_MIME=image/jpeg,image/png,image/webp
MEDIA_SOFT_DELETE_DAYS=30
MEDIA_PRESIGN_TTL_SECONDS=300
```

## 4) CORS del bucket
Permitir origenes del panel admin y localhost dev.
Minimo requerido para upload directo por presigned URL:
- metodos: `PUT`, `GET`, `HEAD`
- headers: `*`
- exponer `ETag`

## 5) Despliegue backend
1. Desplegar version con soporte R2.
2. Ejecutar migraciones.
3. Confirmar healthcheck `GET /health/`.
4. Probar flujo:
   - `POST /api/v1/media/uploads/presign/`
   - upload `PUT` directo a R2
   - `POST /api/v1/media/uploads/complete/`
   - attach en `POST /api/v1/products/{id}/images/`

## 6) Cron obligatorio de purge
- Programar ejecucion diaria de:

```bash
python manage.py purge_soft_deleted_media
```

- Objetivo: limpiar objetos huérfanos vencidos (`delete_after <= now`) y registros en DB.

## 7) Observabilidad minima
- Revisar logs de eventos:
  - `media.upload.complete`
  - `product_image.attach`
  - `product_image.update`
  - `product_image.delete`
  - `media.purge`
- Alertar si:
  - fallos repetidos de `complete`
  - crecimiento anormal del bucket
  - purge diario no ejecutado

## 8) Checklist de release a produccion
1. Bucket prod creado y sin mezclar datos de staging.
2. CORS validado con dominio real del admin.
3. Variables backend cargadas en prod.
4. Variables frontend cargadas en prod.
5. `next.config.ts` aceptando host de media prod.
6. Smoke test de carga y render en panel + storefront.
7. Cron `purge_soft_deleted_media` activo.
