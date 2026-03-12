from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.audit.models import AuditLog
from apps.catalog.models import MediaAsset, MediaAssetStatus, MediaProvider, Product, ProductImage
from apps.inventory.models import InventoryMovement, MovementType

User = get_user_model()


class CatalogBaseAPITestCase(APITestCase):
    def create_and_auth_admin(self, username: str = "admin"):
        User.objects.create_user(username=username, password="admin123", role="ADMIN")
        response = self.client.post(
            "/api/v1/auth/token/",
            {"username": username, "password": "admin123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")


class CatalogAuditTests(CatalogBaseAPITestCase):
    def setUp(self):
        self.create_and_auth_admin()

    def test_product_create_update_delete_are_audited(self):
        created = self.client.post(
            "/api/v1/products/",
            {"sku": "CAT-001", "name": "Casco", "default_price": "100.00", "cost_price": "80.00", "is_active": True},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        product_id = created.data["id"]
        self.assertEqual(created.data["cost_price"], "80.00")

        updated = self.client.patch(
            f"/api/v1/products/{product_id}/",
            {"default_price": "120.00", "cost_price": "90.00"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["cost_price"], "90.00")

        deleted = self.client.delete(f"/api/v1/products/{product_id}/")
        self.assertEqual(deleted.status_code, 204)

        self.assertTrue(AuditLog.objects.filter(action="catalog.product.create", entity_id=product_id).exists())
        self.assertTrue(AuditLog.objects.filter(action="catalog.product.update", entity_id=product_id).exists())
        self.assertTrue(AuditLog.objects.filter(action="catalog.product.delete", entity_id=product_id).exists())

    def test_product_stock_adjustment_requires_reason_and_creates_inventory_movement(self):
        product = Product.objects.create(sku="CAT-003", name="Botas", default_price=Decimal("120.00"))

        missing_reason = self.client.patch(
            f"/api/v1/products/{product.id}/",
            {"stock": "5.00"},
            format="json",
        )
        self.assertEqual(missing_reason.status_code, 400)
        self.assertIn("stock_adjust_reason", missing_reason.data["fields"])
        self.assertEqual(InventoryMovement.objects.filter(product=product).count(), 0)

        adjusted = self.client.patch(
            f"/api/v1/products/{product.id}/",
            {"stock": "5.00", "stock_adjust_reason": "Conteo inicial"},
            format="json",
        )
        self.assertEqual(adjusted.status_code, 200)
        self.assertEqual(adjusted.data["stock"], "5.00")

        movement = InventoryMovement.objects.get(product=product)
        self.assertEqual(str(movement.quantity_delta), "5.00")
        self.assertEqual(movement.note, "Conteo inicial")


class MediaUploadApiTests(CatalogBaseAPITestCase):
    def setUp(self):
        self.create_and_auth_admin("admin_media")

    @patch("apps.catalog.views.presign_put_object")
    def test_media_upload_presign_returns_upload_targets(self, presign_mock):
        presign_mock.side_effect = [
            {"method": "PUT", "url": "https://example.com/original", "headers": {"Content-Type": "image/jpeg"}, "object_key": "products/original/a.jpg"},
            {"method": "PUT", "url": "https://example.com/thumb", "headers": {"Content-Type": "image/webp"}, "object_key": "products/thumb/a.webp"},
        ]

        payload = {
            "original": {
                "filename": "casco.jpg",
                "mime": "image/jpeg",
                "size": 120000,
                "width": 1200,
                "height": 1200,
            },
            "thumb": {
                "filename": "casco-thumb.webp",
                "mime": "image/webp",
                "size": 12000,
                "width": 480,
                "height": 480,
            },
        }

        response = self.client.post("/api/v1/media/uploads/presign/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("upload_token", response.data)
        self.assertEqual(response.data["original"]["method"], "PUT")
        self.assertEqual(response.data["thumb"]["method"], "PUT")

    @patch("apps.catalog.views.build_public_url")
    @patch("apps.catalog.views.ensure_object_exists")
    @patch("apps.catalog.views.parse_upload_token")
    def test_media_upload_complete_creates_asset_and_audit(self, parse_token_mock, ensure_exists_mock, build_public_url_mock):
        parse_token_mock.return_value = {
            "bucket": "bucket-test",
            "object_key_original": "products/original/abc.jpg",
            "object_key_thumb": "products/thumb/abc.webp",
            "original": {
                "mime": "image/jpeg",
                "size": 40000,
                "width": 1200,
                "height": 1200,
            },
            "thumb": {
                "mime": "image/webp",
                "size": 8000,
                "width": 480,
                "height": 480,
            },
        }
        build_public_url_mock.side_effect = [
            "https://public.r2.dev/products/original/abc.jpg",
            "https://public.r2.dev/products/thumb/abc.webp",
        ]

        response = self.client.post("/api/v1/media/uploads/complete/", {"upload_token": "token"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("asset_id", response.data)

        asset = MediaAsset.objects.get(id=response.data["asset_id"])
        self.assertEqual(asset.provider, MediaProvider.R2)
        self.assertEqual(asset.status, MediaAssetStatus.READY)
        self.assertTrue(AuditLog.objects.filter(action="media.upload.complete", entity_id=asset.id).exists())
        self.assertEqual(ensure_exists_mock.call_count, 2)


class ProductImagesApiTests(CatalogBaseAPITestCase):
    def setUp(self):
        self.create_and_auth_admin("admin_images")
        self.product = Product.objects.create(sku="PRD-001", name="Casco", default_price=Decimal("399.00"), is_active=True)
        self.asset_1 = MediaAsset.objects.create(
            provider=MediaProvider.R2,
            bucket="b",
            object_key_original="products/original/1.jpg",
            object_key_thumb="products/thumb/1.webp",
            public_url_original="https://public.r2.dev/products/original/1.jpg",
            public_url_thumb="https://public.r2.dev/products/thumb/1.webp",
            mime_type="image/jpeg",
            size_bytes=100,
            width=1000,
            height=1000,
            status=MediaAssetStatus.READY,
        )
        self.asset_2 = MediaAsset.objects.create(
            provider=MediaProvider.R2,
            bucket="b",
            object_key_original="products/original/2.jpg",
            object_key_thumb="products/thumb/2.webp",
            public_url_original="https://public.r2.dev/products/original/2.jpg",
            public_url_thumb="https://public.r2.dev/products/thumb/2.webp",
            mime_type="image/jpeg",
            size_bytes=100,
            width=900,
            height=900,
            status=MediaAssetStatus.READY,
        )

    def test_attach_list_patch_delete_product_images(self):
        attach_first = self.client.post(
            f"/api/v1/products/{self.product.id}/images/",
            {"asset_id": str(self.asset_1.id), "is_primary": True, "sort_order": 0},
            format="json",
        )
        self.assertEqual(attach_first.status_code, 201)
        first_image_id = attach_first.data["id"]
        self.assertTrue(attach_first.data["is_primary"])

        attach_second = self.client.post(
            f"/api/v1/products/{self.product.id}/images/",
            {"asset_id": str(self.asset_2.id), "sort_order": 1},
            format="json",
        )
        self.assertEqual(attach_second.status_code, 201)
        second_image_id = attach_second.data["id"]

        listed = self.client.get(f"/api/v1/products/{self.product.id}/images/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 2)

        make_second_primary = self.client.patch(
            f"/api/v1/products/{self.product.id}/images/{second_image_id}/",
            {"is_primary": True},
            format="json",
        )
        self.assertEqual(make_second_primary.status_code, 200)
        self.assertTrue(make_second_primary.data["is_primary"])

        delete_first = self.client.delete(f"/api/v1/products/{self.product.id}/images/{first_image_id}/")
        self.assertEqual(delete_first.status_code, 204)

        self.asset_1.refresh_from_db()
        self.assertEqual(self.asset_1.status, MediaAssetStatus.SOFT_DELETED)
        self.assertIsNotNone(self.asset_1.delete_after)

        delete_second = self.client.delete(f"/api/v1/products/{self.product.id}/images/{second_image_id}/")
        self.assertEqual(delete_second.status_code, 204)

        self.asset_2.refresh_from_db()
        self.assertEqual(self.asset_2.status, MediaAssetStatus.SOFT_DELETED)


class PublicCatalogTests(APITestCase):
    def setUp(self):
        self.active = Product.objects.create(sku="PUB-001", name="Casco Publico", default_price=Decimal("150.00"), is_active=True)
        self.inactive = Product.objects.create(
            sku="PUB-002",
            name="Casco Inactivo",
            default_price=Decimal("180.00"),
            is_active=False,
        )
        asset_1 = MediaAsset.objects.create(
            provider=MediaProvider.EXTERNAL,
            bucket="",
            object_key_original="",
            object_key_thumb="",
            public_url_original="https://example.com/primary.jpg",
            public_url_thumb="https://example.com/primary-thumb.jpg",
            mime_type="image/jpeg",
            size_bytes=0,
            width=0,
            height=0,
            status=MediaAssetStatus.READY,
        )
        asset_2 = MediaAsset.objects.create(
            provider=MediaProvider.EXTERNAL,
            bucket="",
            object_key_original="",
            object_key_thumb="",
            public_url_original="https://example.com/secondary.jpg",
            public_url_thumb="https://example.com/secondary-thumb.jpg",
            mime_type="image/jpeg",
            size_bytes=0,
            width=0,
            height=0,
            status=MediaAssetStatus.READY,
        )
        self.primary_image = ProductImage.objects.create(product=self.active, asset=asset_1, is_primary=True, sort_order=0)
        ProductImage.objects.create(product=self.active, asset=asset_2, is_primary=False, sort_order=1)

    def test_public_catalog_list_is_readonly_and_does_not_require_auth(self):
        response = self.client.get("/api/v1/public/catalog/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["sku"], "PUB-001")
        self.assertEqual(response.data["results"][0]["primary_image_id"], str(self.primary_image.id))
        self.assertEqual(len(response.data["results"][0]["images"]), 2)

        post = self.client.post(
            "/api/v1/public/catalog/",
            {"sku": "X", "name": "X", "default_price": "1.00"},
            format="json",
        )
        self.assertEqual(post.status_code, 405)

    def test_public_catalog_search_filters_active_products(self):
        response = self.client.get("/api/v1/public/catalog/?q=casco")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["sku"], "PUB-001")

        response_inactive = self.client.get("/api/v1/public/catalog/?q=inactivo")
        self.assertEqual(response_inactive.status_code, 200)
        self.assertEqual(response_inactive.data["count"], 0)

    def test_public_catalog_detail_by_sku(self):
        response = self.client.get("/api/v1/public/catalog/PUB-001/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sku"], "PUB-001")
        self.assertEqual(response.data["primary_image_id"], str(self.primary_image.id))
        self.assertEqual(len(response.data["images"]), 2)

        not_found = self.client.get("/api/v1/public/catalog/PUB-002/")
        self.assertEqual(not_found.status_code, 404)


class ProductListFiltersTests(CatalogBaseAPITestCase):
    def setUp(self):
        self.create_and_auth_admin("admin_filters")

        self.product_with_stock = Product.objects.create(
            sku="FLT-001",
            name="Casco LS2",
            default_price=Decimal("100.00"),
        )
        self.product_without_stock = Product.objects.create(
            sku="FLT-002",
            name="Guantes AGV",
            default_price=Decimal("80.00"),
        )

        InventoryMovement.objects.create(
            product=self.product_with_stock,
            movement_type=MovementType.INBOUND,
            quantity_delta=Decimal("3.00"),
            reference_type="seed",
            reference_id="seed-1",
            note="seed",
            created_by=User.objects.get(username="admin_filters"),
        )

    def test_products_list_filters_by_stock(self):
        with_stock = self.client.get("/api/v1/products/?has_stock=true")
        self.assertEqual(with_stock.status_code, 200)
        self.assertEqual(with_stock.data["count"], 1)
        self.assertEqual(with_stock.data["results"][0]["sku"], "FLT-001")


class PurgeSoftDeletedMediaCommandTests(APITestCase):
    @patch("apps.catalog.management.commands.purge_soft_deleted_media.delete_object_if_exists")
    def test_command_purges_only_expired_assets(self, delete_object_mock):
        expired = MediaAsset.objects.create(
            provider=MediaProvider.R2,
            bucket="bucket",
            object_key_original="products/original/expired.jpg",
            object_key_thumb="products/thumb/expired.webp",
            public_url_original="https://example.com/expired.jpg",
            public_url_thumb="https://example.com/expired.webp",
            mime_type="image/jpeg",
            size_bytes=1,
            width=10,
            height=10,
            status=MediaAssetStatus.SOFT_DELETED,
            delete_after=timezone.now() - timedelta(days=1),
        )
        MediaAsset.objects.create(
            provider=MediaProvider.R2,
            bucket="bucket",
            object_key_original="products/original/future.jpg",
            object_key_thumb="products/thumb/future.webp",
            public_url_original="https://example.com/future.jpg",
            public_url_thumb="https://example.com/future.webp",
            mime_type="image/jpeg",
            size_bytes=1,
            width=10,
            height=10,
            status=MediaAssetStatus.SOFT_DELETED,
            delete_after=timezone.now() + timedelta(days=1),
        )

        from django.core.management import call_command

        call_command("purge_soft_deleted_media")

        self.assertFalse(MediaAsset.objects.filter(id=expired.id).exists())
        self.assertEqual(delete_object_mock.call_count, 2)
        self.assertTrue(AuditLog.objects.filter(action="media.purge").exists())
