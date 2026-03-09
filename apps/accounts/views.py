from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import UserCreateSerializer, UserListSerializer, UserUpdateSerializer
from apps.accounts.throttles import PasswordResetThrottle
from apps.audit.services import record_audit
from apps.common.permissions import RolePermission


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [RolePermission]
    capability_map = {
        "list": ["users.manage"],
        "retrieve": ["users.manage"],
        "create": ["users.manage"],
        "partial_update": ["users.manage"],
        "update": ["users.manage"],
        "destroy": ["users.manage"],
    }

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserListSerializer

    def get_queryset(self):
        qs = User.objects.select_related("investor_profile").order_by("-date_joined")
        query = self.request.query_params.get("q")
        if query:
            terms = query.split()
            for term in terms:
                qs = qs.filter(
                    Q(first_name__icontains=term)
                    | Q(last_name__icontains=term)
                    | Q(email__icontains=term)
                )
        return qs

    def perform_create(self, serializer):
        user = serializer.save()
        record_audit(
            actor=self.request.user,
            action="user.create",
            entity_type="user",
            entity_id=user.id,
            payload={
                "email": user.email,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        )

    def perform_update(self, serializer):
        old_user = self.get_object()
        old_snapshot = {
            "first_name": old_user.first_name,
            "last_name": old_user.last_name,
            "role": old_user.role,
            "is_active": old_user.is_active,
        }
        user = serializer.save()
        new_snapshot = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
        }
        record_audit(
            actor=self.request.user,
            action="user.update",
            entity_type="user",
            entity_id=user.id,
            payload={"before": old_snapshot, "after": new_snapshot},
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"code": "method_not_allowed", "detail": "No se permite eliminar usuarios. Use is_active.", "fields": {}},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        output = UserListSerializer(serializer.instance).data
        return Response(output, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        output = UserListSerializer(serializer.instance).data
        return Response(output)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response(
                {"code": "validation_error", "detail": "Email es requerido.", "fields": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Always return generic message (OWASP: don't reveal if email exists)
        generic = {"detail": "Si el email está registrado, recibirás un enlace para restablecer tu contraseña."}

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return Response(generic)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{settings.FRONTEND_BASE_URL}/restablecer-contrasena?uid={uid}&token={token}"

        html_message = render_to_string(
            "accounts/password_reset_email.html",
            {"user": user, "reset_url": reset_url},
        )

        send_mail(
            subject="Restablecer contraseña — MotoIsla",
            message=f"Hola {user.first_name},\n\nVisita este enlace para restablecer tu contraseña:\n{reset_url}\n\nEste enlace expira en 1 hora.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
        )

        record_audit(
            actor=None,
            action="password_reset.request",
            entity_type="user",
            entity_id=user.id,
            payload={"email": user.email},
        )

        return Response(generic)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        uid = request.data.get("uid", "")
        token = request.data.get("token", "")
        new_password = request.data.get("new_password", "")

        if not uid or not token or not new_password:
            return Response(
                {"code": "validation_error", "detail": "uid, token y new_password son requeridos.", "fields": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (ValueError, TypeError, User.DoesNotExist):
            return Response(
                {"code": "invalid_token", "detail": "El enlace es inválido o ha expirado.", "fields": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"code": "invalid_token", "detail": "El enlace es inválido o ha expirado.", "fields": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            password_validation.validate_password(new_password, user)
        except DjangoValidationError as e:
            return Response(
                {"code": "validation_error", "detail": "La contraseña no cumple los requisitos.", "fields": {"new_password": e.messages}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        record_audit(
            actor=None,
            action="password_reset.confirm",
            entity_type="user",
            entity_id=user.id,
            payload={"email": user.email},
        )

        return Response({"detail": "Contraseña actualizada exitosamente."})
