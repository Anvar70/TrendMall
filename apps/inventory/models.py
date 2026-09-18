from django.conf import settings
from django.db import models


class InventoryMovement(models.Model):
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.PROTECT, related_name='movements')
    delta = models.IntegerField()
    type = models.CharField(max_length=16, choices=[(k, k) for k in ['INITIAL', 'RESTOCK', 'ADJUSTMENT', 'ORDER_OUT', 'CANCEL_RETURN']])
    order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [models.UniqueConstraint(fields=['variant', 'order', 'type'], condition=models.Q(type__in=['ORDER_OUT', 'CANCEL_RETURN']), name='one_stock_event_per_order_variant')]
