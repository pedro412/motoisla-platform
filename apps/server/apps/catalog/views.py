from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import generics, serializers, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_audit
from apps.catalog.models import Brand, MediaAsset, MediaAssetStatus, MediaProvider, Product, ProductImage, ProductType
from apps.catalog.querysets import with_inventory_metrics
from apps.catalog.r2 import (
    assert_r2_enabled,
    build_product_object_key,
    build_public_url,
    create_upload_token,
    ensure_object_exists,
    parse_upload_token,
    presign_put_object,
    validate_file_meta,
)
from apps.catalog.serializers import (
    BrandSerializer,
    MediaAssetSerializer,
    MediaUploadCompleteSerializer,
    MediaUploadPresignSerializer,
    ProductImageAttachSerializer,
    ProductImageSerializer,
    ProductImageUpdateSerializer,
    ProductSerializer,
    ProductTypeSerializer,
    PublicCatalogProductSerializer,
)
from apps.catalog.throttles import PublicCatalogAnonThrottle
from apps.common.permissions import RolePermission
from apps.inventory.models import InventoryMovement


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [RolePermission]
    capability_map = {
        "list": ["catalog.view"],
        "retrieve": ["catalog.view"],
        "create": ["catalog.manage"],
        "partial_update": ["catalog.manage"],
        "update": ["catalog.manage"],
        "destroy": ["catalog.manage"],
    }

    def get_queryset(self):
        queryset = with_inventory_metrics(Product.objects.all()).prefetch_related("images__asset")

        include_inactive = self.request.query_params.get("include_inactive", "").strip().lower()
        if include_inactive not in {"1", "true", "yes"}:
            queryset = queryset.filter(is_active=True)

        query = self.request.query_params.get("q")
        if query:
            terms = query.split()
            for term in terms:
                queryset = queryset.filter(Q(name__icontains=term) | Q(sku__icontains=term))

        brand_id = self.request.query_params.get("brand")
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        product_type_id = self.request.query_params.get("product_type")
        if product_type_id:
            queryset = queryset.filter(product_type_id=product_type_id)

        has_stock = self.request.query_params.get("has_stock")
        if has_stock is not None:
            normalized_has_stock = has_stock.strip().lower()
            if normalized_has_stock in {"1", "true", "yes"}:
                queryset = queryset.filter(stock__gt=0)
            elif normalized_has_stock in {"0", "false", "no"}:
                queryset = queryset.filter(stock__lte=0)
        return queryset

    def perform_create(self, serializer):
        product = serializer.save()
        record_audit(
            actor=self.request.user,
            action="catalog.product.create",
            entity_type="product",
            entity_id=product.id,
            payload={
                "sku": product.sku,
                "name": product.name,
                "default_price": str(product.default_price),
                "cost_price": str(product.cost_price) if product.cost_price is not None else None,
                "is_active": product.is_active,
            },
        )

    def perform_update(self, serializer):
        old_product = self.get_object()
        old_snapshot = {
            "sku": old_product.sku,
            "name": old_product.name,
            "default_price": str(old_product.default_price),
            "cost_price": str(old_product.cost_price) if old_product.cost_price is not None else None,
            "stock": str(getattr(old_product, "stock", InventoryMovement.current_stock(old_product.id))),
            "is_active": old_product.is_active,
        }
        product = serializer.save()
        new_snapshot = {
            "sku": product.sku,
            "name": product.name,
            "default_price": str(product.default_price),
            "cost_price": str(product.cost_price) if product.cost_price is not None else None,
            "stock": str(InventoryMovement.current_stock(product.id)),
            "is_active": product.is_active,
        }
        record_audit(
            actor=self.request.user,
            action="catalog.product.update",
            entity_type="product",
            entity_id=product.id,
            payload={"before": old_snapshot, "after": new_snapshot},
        )

    def perform_destroy(self, instance):
        record_audit(
            actor=self.request.user,
            action="catalog.product.delete",
            entity_type="product",
            entity_id=instance.id,
            payload={
                "sku": instance.sku,
                "name": instance.name,
                "default_price": str(instance.default_price),
                "cost_price": str(instance.cost_price) if instance.cost_price is not None else None,
                "is_active": instance.is_active,
            },
        )
        super().perform_destroy(instance)


class MediaUploadPresignView(APIView):
    permission_classes = [RolePermission]
    capability_map = {"post": ["catalog.manage"]}

    def post(self, request):
        serializer = MediaUploadPresignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assert_r2_enabled()

        original = serializer.validated_data["original"]
        thumb = serializer.validated_data["thumb"]

        validate_file_meta(original, field_name="original")
        validate_file_meta(thumb, field_name="thumb")

        original_key = build_product_object_key("original", original["filename"], original["mime"])
        thumb_key = build_product_object_key("thumb", thumb["filename"], thumb["mime"])

        token_payload = {
            "provider": MediaProvider.R2,
            "bucket": settings.R2_BUCKET,
            "object_key_original": original_key,
            "object_key_thumb": thumb_key,
            "original": original,
            "thumb": thumb,
        }
        upload_token = create_upload_token(token_payload)

        return Response(
            {
                "upload_token": upload_token,
                "original": presign_put_object(original_key, original["mime"]),
                "thumb": presign_put_object(thumb_key, thumb["mime"]),
            }
        )


class MediaUploadCompleteView(APIView):
    permission_classes = [RolePermission]
    capability_map = {"post": ["catalog.manage"]}

    def post(self, request):
        serializer = MediaUploadCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assert_r2_enabled()

        token_payload = parse_upload_token(serializer.validated_data["upload_token"])

        object_key_original = token_payload["object_key_original"]
        object_key_thumb = token_payload["object_key_thumb"]

        ensure_object_exists(object_key_original)
        ensure_object_exists(object_key_thumb)

        original_meta = token_payload["original"]

        asset = MediaAsset.objects.create(
            provider=MediaProvider.R2,
            bucket=token_payload["bucket"],
            object_key_original=object_key_original,
            object_key_thumb=object_key_thumb,
            public_url_original=build_public_url(object_key_original),
            public_url_thumb=build_public_url(object_key_thumb),
            mime_type=original_meta["mime"],
            size_bytes=original_meta["size"],
            width=original_meta["width"],
            height=original_meta["height"],
            status=MediaAssetStatus.READY,
        )

        record_audit(
            actor=request.user,
            action="media.upload.complete",
            entity_type="media_asset",
            entity_id=asset.id,
            payload={
                "provider": asset.provider,
                "bucket": asset.bucket,
                "object_key_original": asset.object_key_original,
                "object_key_thumb": asset.object_key_thumb,
            },
        )

        return Response({"asset_id": str(asset.id), "asset": MediaAssetSerializer(asset).data}, status=status.HTTP_201_CREATED)


def _schedule_soft_delete_if_orphan(asset):
    if asset.product_images.exists() or asset.status == MediaAssetStatus.SOFT_DELETED:
        return

    days = int(getattr(settings, "MEDIA_SOFT_DELETE_DAYS", 30))
    asset.status = MediaAssetStatus.SOFT_DELETED
    asset.delete_after = timezone.now() + timedelta(days=days)
    asset.save(update_fields=["status", "delete_after", "updated_at"])


def _restore_asset_if_soft_deleted(asset):
    if asset.status != MediaAssetStatus.SOFT_DELETED:
        return

    asset.status = MediaAssetStatus.READY
    asset.delete_after = None
    asset.save(update_fields=["status", "delete_after", "updated_at"])


class ProductImageListCreateView(APIView):
    permission_classes = [RolePermission]
    capability_map = {
        "get": ["catalog.view"],
        "post": ["catalog.manage"],
    }

    @staticmethod
    def _get_product(product_id):
        return get_object_or_404(Product.objects.prefetch_related("images__asset"), id=product_id)

    def get(self, request, product_id):
        product = self._get_product(product_id)
        images = product.images.select_related("asset").order_by("-is_primary", "sort_order", "created_at")
        return Response(ProductImageSerializer(images, many=True).data)

    def post(self, request, product_id):
        product = self._get_product(product_id)
        serializer = ProductImageAttachSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        asset = serializer.context["asset"]
        is_primary = serializer.validated_data.get("is_primary")
        sort_order = serializer.validated_data.get("sort_order")

        with transaction.atomic():
            _restore_asset_if_soft_deleted(asset)

            existing_count = product.images.count()
            if is_primary is None:
                is_primary = existing_count == 0

            if sort_order is None:
                max_sort = product.images.aggregate(value=Max("sort_order")).get("value")
                sort_order = 0 if max_sort is None else max_sort + 1

            if is_primary:
                product.images.filter(is_primary=True).update(is_primary=False)

            try:
                image = ProductImage.objects.create(
                    product=product,
                    asset=asset,
                    is_primary=is_primary,
                    sort_order=sort_order,
                )
            except IntegrityError as exc:
                raise serializers.ValidationError({"detail": "No fue posible asociar la imagen al producto."}) from exc

        record_audit(
            actor=request.user,
            action="product_image.attach",
            entity_type="product_image",
            entity_id=image.id,
            payload={
                "product_id": str(product.id),
                "asset_id": str(asset.id),
                "is_primary": image.is_primary,
                "sort_order": image.sort_order,
            },
        )

        return Response(ProductImageSerializer(image).data, status=status.HTTP_201_CREATED)


class ProductImageDetailView(APIView):
    permission_classes = [RolePermission]
    capability_map = {
        "patch": ["catalog.manage"],
        "delete": ["catalog.manage"],
    }

    @staticmethod
    def _get_product_image(product_id, image_id):
        product = get_object_or_404(Product, id=product_id)
        image = get_object_or_404(ProductImage.objects.select_related("asset"), id=image_id, product=product)
        return product, image

    def patch(self, request, product_id, image_id):
        product, image = self._get_product_image(product_id, image_id)
        serializer = ProductImageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_primary = serializer.validated_data.get("is_primary", image.is_primary)
        sort_order = serializer.validated_data.get("sort_order", image.sort_order)

        old_snapshot = {"is_primary": image.is_primary, "sort_order": image.sort_order}

        with transaction.atomic():
            if is_primary:
                product.images.filter(is_primary=True).exclude(id=image.id).update(is_primary=False)

            image.is_primary = is_primary
            image.sort_order = sort_order
            image.save(update_fields=["is_primary", "sort_order", "updated_at"])

        record_audit(
            actor=request.user,
            action="product_image.update",
            entity_type="product_image",
            entity_id=image.id,
            payload={"before": old_snapshot, "after": {"is_primary": image.is_primary, "sort_order": image.sort_order}},
        )

        return Response(ProductImageSerializer(image).data)

    def delete(self, request, product_id, image_id):
        product, image = self._get_product_image(product_id, image_id)
        asset = image.asset
        was_primary = image.is_primary

        with transaction.atomic():
            image_id_value = image.id
            image.delete()

            if was_primary:
                next_image = product.images.order_by("sort_order", "created_at").first()
                if next_image and not next_image.is_primary:
                    next_image.is_primary = True
                    next_image.save(update_fields=["is_primary", "updated_at"])

            _schedule_soft_delete_if_orphan(asset)

        record_audit(
            actor=request.user,
            action="product_image.delete",
            entity_type="product_image",
            entity_id=image_id_value,
            payload={"product_id": str(product.id), "asset_id": str(asset.id)},
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all().order_by("name")
    serializer_class = BrandSerializer
    permission_classes = [RolePermission]
    capability_map = {
        "list": ["catalog.view"],
        "retrieve": ["catalog.view"],
        "create": ["imports.manage"],
        "update": ["catalog.manage"],
        "partial_update": ["catalog.manage"],
        "destroy": ["catalog.manage"],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get("q")
        if query:
            query = query.strip()
            queryset = queryset.filter(Q(name__icontains=query) | Q(normalized_name__icontains=query))
        return queryset


class ProductTypeViewSet(viewsets.ModelViewSet):
    queryset = ProductType.objects.all().order_by("name")
    serializer_class = ProductTypeSerializer
    permission_classes = [RolePermission]
    capability_map = {
        "list": ["catalog.view"],
        "retrieve": ["catalog.view"],
        "create": ["imports.manage"],
        "update": ["catalog.manage"],
        "partial_update": ["catalog.manage"],
        "destroy": ["catalog.manage"],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get("q")
        if query:
            query = query.strip()
            queryset = queryset.filter(Q(name__icontains=query) | Q(normalized_name__icontains=query))
        return queryset


@method_decorator(cache_page(settings.PUBLIC_CATALOG_CACHE_TTL_SECONDS), name="dispatch")
class PublicCatalogListView(generics.ListAPIView):
    serializer_class = PublicCatalogProductSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PublicCatalogAnonThrottle]

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).prefetch_related("images__asset").order_by("name")
        query = self.request.query_params.get("q")
        if query:
            query = query.strip()
            queryset = queryset.filter(Q(name__icontains=query) | Q(sku__icontains=query))
        return queryset


@method_decorator(cache_page(settings.PUBLIC_CATALOG_CACHE_TTL_SECONDS), name="dispatch")
class PublicCatalogDetailView(generics.RetrieveAPIView):
    serializer_class = PublicCatalogProductSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PublicCatalogAnonThrottle]
    lookup_field = "sku"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).prefetch_related("images__asset")
