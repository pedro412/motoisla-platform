from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.catalog.views import (
    BrandViewSet,
    MediaUploadCompleteView,
    MediaUploadPresignView,
    ProductImageDetailView,
    ProductImageListCreateView,
    ProductTypeViewSet,
    ProductViewSet,
    PublicCatalogDetailView,
    PublicCatalogListView,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("brands", BrandViewSet, basename="brand")
router.register("product-types", ProductTypeViewSet, basename="product-type")

urlpatterns = [
    path("media/uploads/presign/", MediaUploadPresignView.as_view(), name="media-upload-presign"),
    path("media/uploads/complete/", MediaUploadCompleteView.as_view(), name="media-upload-complete"),
    path("products/<uuid:product_id>/images/", ProductImageListCreateView.as_view(), name="product-images"),
    path("products/<uuid:product_id>/images/<uuid:image_id>/", ProductImageDetailView.as_view(), name="product-image-detail"),
    path("public/catalog/", PublicCatalogListView.as_view(), name="public-catalog-list"),
    path("public/catalog/<str:sku>/", PublicCatalogDetailView.as_view(), name="public-catalog-detail"),
]
urlpatterns += router.urls
