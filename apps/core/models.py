from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from apps.core.uploads import image_path, validate_image


class StoreSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    name = models.CharField(max_length=100, default='TrendBox')
    logo = models.ImageField(upload_to=image_path, validators=[validate_image], blank=True)
    landing_uz = models.TextField(blank=True)
    landing_ru = models.TextField(blank=True)
    landing_en = models.TextField(blank=True)
    support_phone = models.CharField(max_length=30, blank=True)
    support_email = models.EmailField(blank=True)
    shipping_fee = models.DecimalField(max_digits=14, decimal_places=2, default=25000, validators=[MinValueValidator(0)])
    default_low_stock_threshold = models.PositiveIntegerField(default=5)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name='store_singleton'),
                       models.CheckConstraint(condition=models.Q(shipping_fee__gte=0), name='shipping_nonnegative')]

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=80)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
