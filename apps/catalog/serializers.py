import uuid
from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import Brand, MediaAsset, MediaAssetStatus, Product, ProductImage, ProductType
from apps.inventory.models import InventoryMovement, MovementType
from apps.purchases.models import PurchaseReceipt, PurchaseReceiptLine, ReceiptStatus
from apps.suppliers.models import Supplier

IVA_RATE = Decimal("0.16")


class MediaAssetSerializer(serializers.ModelSerializer):
    original_url = serializers.CharField(source="public_url_original", read_only=True)
    thumb_url = serializers.CharField(source="public_url_thumb", read_only=True)

    class Meta:
        model = MediaAsset
        fields = [
            "id",
            "provider",
            "status",
            "original_url",
            "thumb_url",
            "mime_type",
            "width",
            "height",
            "size_bytes",
        ]
        read_only_fields = fields


class ProductImageSerializer(serializers.ModelSerializer):
    asset_id = serializers.UUIDField(source="asset.id", read_only=True)
    original_url = serializers.CharField(source="asset.public_url_original", read_only=True)
    thumb_url = serializers.CharField(source="asset.public_url_thumb", read_only=True)
    width = serializers.IntegerField(source="asset.width", read_only=True)
    height = serializers.IntegerField(source="asset.height", read_only=True)
    mime_type = serializers.CharField(source="asset.mime_type", read_only=True)

    class Meta:
        model = ProductImage
        fields = [
            "id",
            "asset_id",
            "is_primary",
            "sort_order",
            "original_url",
            "thumb_url",
            "width",
            "height",
            "mime_type",
        ]
        read_only_fields = fields


class ProductImageAttachSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField()
    is_primary = serializers.BooleanField(required=False)
    sort_order = serializers.IntegerField(required=False, min_value=0)

    def validate_asset_id(self, value):
        try:
            asset = MediaAsset.objects.get(id=value)
        except MediaAsset.DoesNotExist as exc:
            raise serializers.ValidationError("El asset no existe.") from exc

        if asset.status != MediaAssetStatus.READY:
            raise serializers.ValidationError("El asset no está listo para asociarse.")

        self.context["asset"] = asset
        return value


class ProductImageUpdateSerializer(serializers.Serializer):
    is_primary = serializers.BooleanField(required=False)
    sort_order = serializers.IntegerField(required=False, min_value=0)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Debes enviar al menos un campo para actualizar.")
        return attrs


class MediaUploadFileMetaSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    mime = serializers.CharField(max_length=80)
    size = serializers.IntegerField(min_value=1)
    width = serializers.IntegerField(min_value=1)
    height = serializers.IntegerField(min_value=1)


class MediaUploadPresignSerializer(serializers.Serializer):
    original = MediaUploadFileMetaSerializer()
    thumb = MediaUploadFileMetaSerializer()


class MediaUploadCompleteSerializer(serializers.Serializer):
    upload_token = serializers.CharField()


class ProductSerializer(serializers.ModelSerializer):
    stock = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, write_only=True)
    stock_adjust_reason = serializers.CharField(write_only=True, required=False, allow_blank=True)
    primary_image_id = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    product_type_name = serializers.CharField(source="product_type.name", read_only=True)
    investor_assignable_qty = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "default_price",
            "cost_price",
            "brand",
            "brand_name",
            "product_type",
            "product_type_name",
            "brand_label",
            "product_type_label",
            "is_active",
            "stock",
            "stock_adjust_reason",
            "primary_image_id",
            "images",
            "investor_assignable_qty",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "primary_image_id", "images", "investor_assignable_qty"]

    @staticmethod
    def _ordered_images(obj):
        images = list(obj.images.all())
        images.sort(key=lambda image: (0 if image.is_primary else 1, image.sort_order, image.created_at))
        return images

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and request.method in {"POST", "PUT", "PATCH"}:
            current_stock = InventoryMovement.current_stock(instance.id)
        else:
            current_stock = getattr(instance, "stock", None)
            if current_stock is None:
                current_stock = InventoryMovement.current_stock(instance.id)
        data["stock"] = f"{current_stock:.2f}"
        return data

    def get_primary_image_id(self, obj):
        image = next((image for image in self._ordered_images(obj) if image.is_primary), None)
        if image:
            return str(image.id)
        first_image = next(iter(self._ordered_images(obj)), None)
        return str(first_image.id) if first_image else None

    def get_images(self, obj):
        return ProductImageSerializer(self._ordered_images(obj), many=True).data

    def get_investor_assignable_qty(self, obj):
        current_stock = getattr(obj, "stock", None)
        if current_stock is None:
            current_stock = InventoryMovement.current_stock(obj.id)

        reserved_qty = getattr(obj, "investor_reserved_qty", None)
        if reserved_qty is None:
            reserved_qty = obj.investor_assignments.aggregate(
                total=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F("qty_assigned") - F("qty_sold"),
                            output_field=DecimalField(max_digits=12, decimal_places=2),
                        )
                    ),
                    Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
                )
            )["total"]

        assignable = current_stock - reserved_qty
        if assignable < 0:
            assignable = Decimal("0.00")
        return f"{assignable:.2f}"

    @staticmethod
    def _get_direct_supplier():
        supplier, _ = Supplier.objects.get_or_create(
            code="DIRECT",
            defaults={"name": "Compra directa"},
        )
        return supplier

    def _create_purchase_receipt(self, product: Product, quantity_delta, reason: str, reference_type: str):
        """Create a PurchaseReceipt + INBOUND movement for positive stock additions with cost."""
        user = self.context["request"].user
        unit_cost = product.cost_price
        subtotal = (unit_cost * quantity_delta).quantize(Decimal("0.01"))
        tax = (subtotal * IVA_RATE).quantize(Decimal("0.01"))
        total = subtotal + tax

        receipt = PurchaseReceipt.objects.create(
            supplier=self._get_direct_supplier(),
            status=ReceiptStatus.POSTED,
            subtotal=subtotal,
            tax=tax,
            total=total,
            created_by=user,
            posted_at=timezone.now(),
        )

        PurchaseReceiptLine.objects.create(
            receipt=receipt,
            product=product,
            qty=quantity_delta,
            unit_cost=unit_cost,
        )

        InventoryMovement.objects.create(
            product=product,
            movement_type=MovementType.INBOUND,
            quantity_delta=quantity_delta,
            reference_type=reference_type,
            reference_id=str(receipt.id),
            note=reason.strip(),
            created_by=user,
        )

    def _create_stock_movement(self, product: Product, target_stock, reason: str, reference_type: str):
        current_stock = InventoryMovement.current_stock(product.id)
        quantity_delta = target_stock - current_stock

        if quantity_delta == 0:
            return

        if not reason.strip():
            raise serializers.ValidationError({"stock_adjust_reason": "La razón del ajuste de stock es obligatoria."})

        # Positive delta with cost_price -> create PurchaseReceipt so it counts in purchase metrics
        if quantity_delta > 0 and product.cost_price is not None and product.cost_price > 0:
            self._create_purchase_receipt(product, quantity_delta, reason, reference_type)
            return

        # Negative delta or no cost -> plain adjustment (no purchase receipt)
        InventoryMovement.objects.create(
            product=product,
            movement_type=MovementType.ADJUSTMENT,
            quantity_delta=quantity_delta,
            reference_type=reference_type,
            reference_id=str(uuid.uuid4()),
            note=reason.strip(),
            created_by=self.context["request"].user,
        )

    def create(self, validated_data):
        target_stock = validated_data.pop("stock", None)
        stock_adjust_reason = validated_data.pop("stock_adjust_reason", "")

        with transaction.atomic():
            product = super().create(validated_data)
            if target_stock is not None:
                self._create_stock_movement(product, target_stock, stock_adjust_reason, "product_create_adjustment")
        return product

    def update(self, instance, validated_data):
        target_stock = validated_data.pop("stock", None)
        stock_adjust_reason = validated_data.pop("stock_adjust_reason", "")

        with transaction.atomic():
            product = super().update(instance, validated_data)
            if target_stock is not None:
                self._create_stock_movement(product, target_stock, stock_adjust_reason, "manual_stock_adjustment")
        return product


class PublicCatalogProductSerializer(serializers.ModelSerializer):
    primary_image_id = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "default_price",
            "primary_image_id",
            "images",
            "updated_at",
        ]
        read_only_fields = fields

    @staticmethod
    def _ordered_images(obj):
        images = list(obj.images.all())
        images.sort(key=lambda image: (0 if image.is_primary else 1, image.sort_order, image.created_at))
        return images

    def get_primary_image_id(self, obj):
        image = next((image for image in self._ordered_images(obj) if image.is_primary), None)
        if image:
            return str(image.id)
        first_image = next(iter(self._ordered_images(obj)), None)
        return str(first_image.id) if first_image else None

    def get_images(self, obj):
        return ProductImageSerializer(self._ordered_images(obj), many=True).data


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "normalized_name", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "normalized_name", "created_at", "updated_at"]


class ProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = ["id", "name", "normalized_name", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "normalized_name", "created_at", "updated_at"]
