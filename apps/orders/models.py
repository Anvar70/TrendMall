import uuid
from django.conf import settings
from django.db import models


def order_number():
    return 'TB-' + uuid.uuid4().hex[:16].upper()


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = 'NEW', 'New'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        PACKING = 'PACKING', 'Packing'
        SHIPPED = 'SHIPPED', 'Shipped'
        DELIVERED = 'DELIVERED', 'Delivered'
        CANCELLED = 'CANCELLED', 'Cancelled'

    public_number = models.CharField(max_length=24, unique=True, default=order_number)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    payment_status = models.CharField(max_length=6, choices=[('UNPAID', 'Unpaid'), ('PAID', 'Paid')], default='UNPAID')
    payment_method = models.CharField(max_length=20, default='CASH_ON_DELIVERY')
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=14, decimal_places=2)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    address_snapshot = models.JSONField()
    comment = models.CharField(max_length=1000, blank=True)
    idempotency_key = models.UUIDField()
    request_fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['customer', 'status', 'created_at']), models.Index(fields=['status', 'created_at'])]
        constraints = [models.UniqueConstraint(fields=['customer', 'idempotency_key'], name='unique_checkout_key'),
            models.CheckConstraint(condition=models.Q(subtotal__gte=0, shipping_fee__gte=0, total__gte=0), name='order_nonnegative_amounts')]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.PROTECT)
    product_name_snapshot = models.JSONField()
    sku_snapshot = models.CharField(max_length=80)
    attributes_snapshot = models.JSONField()
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ['id']
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0, unit_price__gt=0, line_total__gt=0), name='order_item_positive')]


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history')
    old_status = models.CharField(max_length=12, blank=True)
    new_status = models.CharField(max_length=12)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
