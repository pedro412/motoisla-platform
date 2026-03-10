from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import PasswordResetConfirmView, PasswordResetRequestView, PinLoginView, PinSetView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("auth/password-reset-confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/pin-login/", PinLoginView.as_view(), name="pin-login"),
    path("auth/pin/", PinSetView.as_view(), name="pin-set"),
    path("", include(router.urls)),
]
