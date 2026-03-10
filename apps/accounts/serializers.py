from django.contrib.auth import password_validation
from django.contrib.auth.models import Group
from rest_framework import serializers

from apps.accounts.models import User, UserRole
from apps.investors.models import Investor


class UserListSerializer(serializers.ModelSerializer):
    investor_profile_id = serializers.SerializerMethodField()
    has_pin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "date_joined",
            "last_login",
            "investor_profile_id",
            "has_pin",
        ]
        read_only_fields = fields

    def get_investor_profile_id(self, obj):
        profile = getattr(obj, "investor_profile", None)
        if profile:
            return str(profile.id)
        return None

    def get_has_pin(self, obj):
        return bool(obj.pin_hash)


class UserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=UserRole.choices)
    password = serializers.CharField(write_only=True, min_length=8)
    investor_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value.lower()

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def validate(self, attrs):
        role = attrs.get("role")
        investor_id = attrs.get("investor_id")
        if investor_id and role != UserRole.INVESTOR:
            raise serializers.ValidationError(
                {"investor_id": "Solo se puede vincular un perfil de inversionista al rol INVESTOR."}
            )
        if investor_id:
            try:
                investor = Investor.objects.get(id=investor_id)
            except Investor.DoesNotExist:
                raise serializers.ValidationError({"investor_id": "Inversionista no encontrado."})
            if investor.user_id is not None:
                raise serializers.ValidationError(
                    {"investor_id": "Este perfil de inversionista ya está vinculado a otro usuario."}
                )
            attrs["_investor"] = investor
        return attrs

    def create(self, validated_data):
        investor = validated_data.pop("_investor", None)
        investor_id = validated_data.pop("investor_id", None)  # noqa: F841
        password = validated_data.pop("password")
        role = validated_data.pop("role")

        user = User(
            username=validated_data["email"],
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role=role,
        )
        user.set_password(password)
        user.save()

        group, _ = Group.objects.get_or_create(name=role)
        user.groups.set([group])

        if investor:
            investor.user = user
            investor.save(update_fields=["user"])

        return user


class UserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    role = serializers.ChoiceField(choices=UserRole.choices, required=False)
    is_active = serializers.BooleanField(required=False)
    investor_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        role = attrs.get("role", self.instance.role)
        investor_id = attrs.get("investor_id")
        if investor_id and role != UserRole.INVESTOR:
            raise serializers.ValidationError(
                {"investor_id": "Solo se puede vincular un perfil de inversionista al rol INVESTOR."}
            )
        if investor_id:
            try:
                investor = Investor.objects.get(id=investor_id)
            except Investor.DoesNotExist:
                raise serializers.ValidationError({"investor_id": "Inversionista no encontrado."})
            if investor.user_id is not None and investor.user_id != self.instance.id:
                raise serializers.ValidationError(
                    {"investor_id": "Este perfil de inversionista ya está vinculado a otro usuario."}
                )
            attrs["_investor"] = investor
        return attrs

    def update(self, instance, validated_data):
        investor = validated_data.pop("_investor", None)
        investor_id = validated_data.pop("investor_id", None)
        new_role = validated_data.get("role")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if new_role and new_role != instance.role:
            instance.role = new_role
            group, _ = Group.objects.get_or_create(name=new_role)
            instance.groups.set([group])

        instance.save()

        if investor_id is not None:
            # Unlink previous investor if any
            Investor.objects.filter(user=instance).update(user=None)
            if investor:
                investor.user = instance
                investor.save(update_fields=["user"])
        elif investor_id is None and "investor_id" in self.initial_data:
            # Explicitly set to null — unlink
            Investor.objects.filter(user=instance).update(user=None)

        return instance
