from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        
        extra_fields.setdefault("is_active", True) 

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        
        # Superusers must be active immediately to log in to the admin panel
        extra_fields.setdefault("is_active", True)

        if not extra_fields.get("is_staff") or not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_staff=True and is_superuser=True.")
        
        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Custom user model:
    - Uses email as unique identifier (no username).
    - Includes specific professional details.
    - Inherits first_name and last_name from AbstractUser.
    """
    username = None
    email = models.EmailField(_("email address"), unique=True)

    ROLE_ADMIN = "admin"
    ROLE_MANAGER = "manager"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_MANAGER, "Manager"),
        (ROLE_MEMBER, "Member"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)

    # New Fields
    department = models.CharField(max_length=100, blank=True)

    # Note: first_name and last_name are inherited from AbstractUser
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [] # Email & Password are required by default

    objects = CustomUserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ("email",)

    def __str__(self):
        # Return Name if available, otherwise Email
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.email})"
        return self.email

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    @property
    def is_manager(self):
        return self.role == self.ROLE_MANAGER

    @property
    def is_member(self):
        return self.role == self.ROLE_MEMBER