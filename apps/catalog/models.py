from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from apps.core.uploads import image_path, validate_image


class TranslatedName(models.Model):
    name_uz = models.CharField(max_length=180)
    name_ru = models.CharField(max_length=180, blank=True)
    name_en = models.CharField(max_length=180, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name_uz


class Category(TranslatedName):
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to=image_path, validators=[validate_image], blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'id']


class Product(TranslatedName):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    slug = models.SlugField(unique=True)
    short_description_uz = models.CharField(max_length=300, blank=True)
    short_description_ru = models.CharField(max_length=300, blank=True)
    short_description_en = models.CharField(max_length=300, blank=True)
    description_uz = models.TextField(blank=True)
    description_ru = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=image_path, validators=[validate_image])
    alt_uz = models.CharField(max_length=180, blank=True)
    alt_ru = models.CharField(max_length=180, blank=True)
    alt_en = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_primary', 'sort_order', 'id']
        constraints = [models.UniqueConstraint(fields=['product'], condition=models.Q(is_primary=True), name='one_primary_product_image')]


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=80, unique=True)
    attributes = models.JSONField(default=dict, blank=True)
    canonical_attribute_key = models.CharField(max_length=500, editable=False, default='{}')
    price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    compare_at_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to=image_path, validators=[validate_image], blank=True)
    stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['product', 'canonical_attribute_key'], name='unique_product_attributes'),
            models.CheckConstraint(condition=models.Q(price__gt=0), name='variant_positive_price'),
            models.CheckConstraint(condition=models.Q(compare_at_price__isnull=True) | models.Q(compare_at_price__gt=models.F('price')), name='variant_compare_price'),
        ]

    def save(self, *args, **kwargs):
        import json
        self.attributes = {str(k).strip().lower(): str(v).strip().lower() for k, v in self.attributes.items()}
        self.canonical_attribute_key = json.dumps(self.attributes, sort_keys=True, ensure_ascii=True, separators=(',', ':'))
        super().save(*args, **kwargs)
