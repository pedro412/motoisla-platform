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

    objects = UserManager()
