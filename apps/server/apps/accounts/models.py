from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    CASHIER = "CASHIER", "Cashier"
    INVESTOR = "INVESTOR", "Investor"


class UserManager(DjangoUserManager):
    def _create_user(self, username, email, password, **extra_fields):
        if not email:
            email = f"{username}@placeholder.local"
        return super()._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CASHIER)
    pin_hash = models.CharField(max_length=128, blank=True, default="")

    objects = UserManager()

    def set_pin(self, raw_pin):
        from django.contrib.auth.hashers import make_password

        self.pin_hash = make_password(raw_pin)

    def check_pin(self, raw_pin):
        from django.contrib.auth.hashers import check_password

        return check_password(raw_pin, self.pin_hash)
