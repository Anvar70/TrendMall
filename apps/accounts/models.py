from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.core.validators import RegexValidator

phone_validator = RegexValidator(r'^\+998\d{9}$', 'Use +998 followed by 9 digits.')


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        user = self.model(email=email.strip().lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.update(is_staff=True, is_superuser=True, role='ADMIN')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        ADMIN = 'ADMIN', 'Admin'

    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=13, validators=[phone_validator])
    role = models.CharField(max_length=8, choices=Role.choices, default=Role.CUSTOMER)
    preferred_language = models.CharField(max_length=2, choices=[('uz', 'Uzbek'), ('ru', 'Russian'), ('en', 'English')], default='uz')
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    marketing_consent = models.BooleanField(default=False)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone']
    objects = UserManager()

    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='user_email_case_insensitive')]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
