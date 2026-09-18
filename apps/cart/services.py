from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from apps.accounts.models import User
from apps.catalog.models import ProductVariant
from apps.core.exceptions import Conflict
from .models import Cart, CartItem


def locked_cart(user):
    # The user lock serializes first-cart creation as well as later checkout/mutations.
    User.objects.select_for_update().get(pk=user.pk)
    cart, _ = Cart.objects.get_or_create(user=user)
    return Cart.objects.select_for_update().get(pk=cart.pk)


def available(variant):
    return variant.is_active and variant.product.is_active and variant.product.category.is_active


@transaction.atomic
def change_cart(user, variant_id=None, item_id=None, quantity=1, remove=False):
    cart = locked_cart(user)
    if item_id is not None:
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        if remove:
            item.delete()
            return
        variant_id = item.variant_id
    else:
        item = cart.items.filter(variant_id=variant_id).first()
        if item:
            quantity += item.quantity
    variant = get_object_or_404(ProductVariant.objects.select_related('product__category'), pk=variant_id)
    if not available(variant) or quantity > variant.stock:
        raise Conflict('The selected quantity is not available.')
    if item:
        item.quantity = quantity
        item.save(update_fields=['quantity'])
    else:
        item = CartItem.objects.create(cart=cart, variant=variant, quantity=quantity, added_price=variant.price)
    return item


def cart_data(user, context):
    from .serializers import CartItemSerializer
    cart, _ = Cart.objects.get_or_create(user=user)
    items = list(cart.items.select_related('variant__product__category').prefetch_related('variant__product__images'))
    return {'id': cart.pk, 'items': CartItemSerializer(items, many=True, context=context).data,
            'subtotal': str(sum((i.variant.price * i.quantity for i in items), Decimal('0.00')))}
