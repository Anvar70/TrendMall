from uuid import uuid4
from django.db import transaction
from django.shortcuts import get_object_or_404
from apps.catalog.models import ProductVariant
from apps.core.exceptions import Conflict
from apps.notifications.services import notify_admins
from .models import InventoryMovement


def move_stock(variant, delta, kind, actor, reason, order=None):
    # Caller must hold the variant row lock inside transaction.atomic.
    before = variant.stock
    if before + delta < 0:
        raise Conflict('Insufficient stock.')
    variant.stock += delta
    variant.save(update_fields=['stock'])
    movement = InventoryMovement.objects.create(variant=variant, delta=delta, type=kind, actor=actor, reason=reason, order=order)
    if before > variant.low_stock_threshold >= variant.stock:
        notify_admins('low_stock', f'low-stock:{movement.pk}', '/admin/inventory/', sku=variant.sku, stock=variant.stock)
    return movement


@transaction.atomic
def adjust_stock(actor, variant_id, delta, reason, kind='ADJUSTMENT'):
    variant = get_object_or_404(ProductVariant.objects.select_for_update(), pk=variant_id)
    return move_stock(variant, delta, kind, actor, reason)
