import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def _guess_mime(url: str) -> str:
    value = (url or "").lower()
    if value.endswith(".png"):
        return "image/png"
    if value.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


def migrate_product_image_urls_to_media_assets(apps, schema_editor):
    ProductImage = apps.get_model("catalog", "ProductImage")
    MediaAsset = apps.get_model("catalog", "MediaAsset")

    product_ids = ProductImage.objects.values_list("product_id", flat=True).distinct()

    for product_id in product_ids:
        images = list(ProductImage.objects.filter(product_id=product_id).order_by("created_at", "id"))
        for index, image in enumerate(images):
            image_url = image.image_url
            asset = MediaAsset.objects.create(
                provider="EXTERNAL",
                bucket="",
                object_key_original="",
                object_key_thumb="",
                public_url_original=image_url,
                public_url_thumb=image_url,
                mime_type=_guess_mime(image_url),
                size_bytes=0,
                width=0,
                height=0,
                status="READY",
                delete_after=None,
            )
            image.asset_id = asset.id
            image.sort_order = index
            image.save(update_fields=["asset", "sort_order"])


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_product_cost_price"),
    ]

    operations = [
        migrations.CreateModel(
            name="MediaAsset",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(choices=[("R2", "Cloudflare R2"), ("EXTERNAL", "External URL")], db_index=True, default="R2", max_length=32)),
                ("bucket", models.CharField(blank=True, max_length=128)),
                ("object_key_original", models.CharField(blank=True, max_length=512)),
                ("object_key_thumb", models.CharField(blank=True, max_length=512)),
                ("public_url_original", models.URLField(max_length=1000)),
                ("public_url_thumb", models.URLField(max_length=1000)),
                ("mime_type", models.CharField(max_length=80)),
                ("size_bytes", models.BigIntegerField(default=0)),
                ("width", models.PositiveIntegerField(default=0)),
                ("height", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(choices=[("UPLOADING", "Uploading"), ("READY", "Ready"), ("SOFT_DELETED", "Soft deleted")], db_index=True, default="UPLOADING", max_length=32)),
                ("delete_after", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="productimage",
            name="asset",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="product_images", to="catalog.mediaasset"),
        ),
        migrations.AddField(
            model_name="productimage",
            name="sort_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="productimage",
            name="updated_at",
            field=models.DateTimeField(default=timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(migrate_product_image_urls_to_media_assets, noop_reverse),
        migrations.RemoveField(
            model_name="productimage",
            name="image_url",
        ),
        migrations.AlterField(
            model_name="productimage",
            name="asset",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="product_images", to="catalog.mediaasset"),
        ),
        migrations.AlterModelOptions(
            name="productimage",
            options={"ordering": ["sort_order", "created_at"]},
        ),
        migrations.AddConstraint(
            model_name="productimage",
            constraint=models.UniqueConstraint(fields=("product", "asset"), name="unique_asset_per_product"),
        ),
    ]
