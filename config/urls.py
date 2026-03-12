from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("backoffice-mi/", admin.site.urls),
    path("health/", include("apps.health.urls")),
    path("api/v1/", include("apps.api_urls")),
]
