import os
import posixpath
import uuid
from pathlib import Path
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.core import signing
from rest_framework import serializers

TOKEN_SALT = "catalog.media.upload.v1"


def _get_required_setting(name: str) -> str:
    value = getattr(settings, name, "")
    if not value:
        raise serializers.ValidationError({"detail": f"Missing media setting: {name}"})
    return value


def _normalized_public_base_url() -> str:
    return _get_required_setting("R2_PUBLIC_BASE_URL").rstrip("/")


def get_r2_client():
    account_id = _get_required_setting("R2_ACCOUNT_ID")
    access_key = _get_required_setting("R2_ACCESS_KEY_ID")
    secret_key = _get_required_setting("R2_SECRET_ACCESS_KEY")

    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def get_file_extension(filename: str, mime: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix

    mime_to_suffix = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    return mime_to_suffix.get(mime, ".bin")


def build_product_object_key(kind: str, filename: str, mime: str) -> str:
    ext = get_file_extension(filename, mime)
    random_name = uuid.uuid4().hex
    return posixpath.join("products", kind, f"{random_name}{ext}")


def build_public_url(object_key: str) -> str:
    return f"{_normalized_public_base_url()}/{quote(object_key)}"


def create_upload_token(payload: dict) -> str:
    return signing.dumps(payload, salt=TOKEN_SALT, compress=True)


def parse_upload_token(token: str) -> dict:
    max_age = int(getattr(settings, "MEDIA_PRESIGN_TTL_SECONDS", 300)) * 3
    try:
        return signing.loads(token, salt=TOKEN_SALT, max_age=max_age)
    except signing.BadSignature as exc:
        raise serializers.ValidationError({"upload_token": "El token de carga es inválido o expiró."}) from exc


def presign_put_object(object_key: str, content_type: str):
    bucket = _get_required_setting("R2_BUCKET")
    client = get_r2_client()
    ttl = int(getattr(settings, "MEDIA_PRESIGN_TTL_SECONDS", 300))
    url = client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": bucket,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=ttl,
    )

    return {
        "method": "PUT",
        "url": url,
        "headers": {
            "Content-Type": content_type,
        },
        "object_key": object_key,
    }


def ensure_object_exists(object_key: str):
    bucket = _get_required_setting("R2_BUCKET")
    client = get_r2_client()

    try:
        client.head_object(Bucket=bucket, Key=object_key)
    except ClientError as exc:
        status_code = int(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 500))
        if status_code == 404:
            raise serializers.ValidationError({"detail": "No se encontró el archivo en storage."}) from exc
        raise


def delete_object_if_exists(object_key: str):
    if not object_key:
        return

    bucket = _get_required_setting("R2_BUCKET")
    client = get_r2_client()

    try:
        client.delete_object(Bucket=bucket, Key=object_key)
    except ClientError as exc:
        status_code = int(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 500))
        if status_code not in {404, 204}:
            raise


def validate_file_meta(meta: dict, *, field_name: str):
    allowed_mime = set(getattr(settings, "MEDIA_ALLOWED_MIME", []))
    max_bytes = int(getattr(settings, "MEDIA_MAX_BYTES", 8 * 1024 * 1024))
    max_dimension = int(getattr(settings, "MEDIA_MAX_DIMENSION", 3000))

    mime = meta.get("mime", "")
    size = int(meta.get("size", 0))
    width = int(meta.get("width", 0))
    height = int(meta.get("height", 0))

    errors: dict[str, list[str]] = {}

    if mime not in allowed_mime:
        errors.setdefault("mime", []).append("Formato no permitido.")
    if size <= 0 or size > max_bytes:
        errors.setdefault("size", []).append(f"Tamaño inválido. Máximo {max_bytes} bytes.")
    if width <= 0 or height <= 0 or width > max_dimension or height > max_dimension:
        errors.setdefault("dimensions", []).append(
            f"Dimensiones inválidas. Máximo {max_dimension}px por lado."
        )

    if errors:
        raise serializers.ValidationError({field_name: errors})


def assert_r2_enabled():
    provider = (getattr(settings, "MEDIA_PROVIDER", "").strip() or "R2").upper()
    if provider != "R2":
        raise serializers.ValidationError({"detail": f"MEDIA_PROVIDER '{provider}' no está soportado en esta versión."})
