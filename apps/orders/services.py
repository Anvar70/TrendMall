import hashlib
import json
from decimal import Decimal
from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from apps.accounts.models import Address
from apps.cart.services import locked_cart, available
from apps.catalog.models import ProductVariant
from apps.core.models import StoreSettings
from apps.core.exceptions import Conflict
from apps.inventory.services import move_stock
from apps.notifications.services import notify, notify_admins
from .models import Order, OrderItem, OrderStatusHistory


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str, ensure_ascii=True).encode()).hexdigest()


def shipping_address(user, data):
    if 'address_id' in data:
        address = get_object_or_404(Address, pk=data['address_id'], user=user)
        return {k: getattr(address, k) for k in ['recipient_name', 'phone', 'region', 'city', 'address_line', 'landmark']}
    return dict(data['address'])


def quote_data(user, cart, data, lock=False):
    items = list(cart.items.order_by('variant_id'))
    if not items:
        raise Conflict('Your cart is empty.')
    variants_qs = ProductVariant.objects.filter(pk__in=[i.variant_id for i in items]).order_by('id')
    if lock:
        variants_qs = variants_qs.select_for_update()
    variants = {v.pk: v for v in variants_qs.select_related('product__category')}
    subtotal = Decimal('0.00')
    rows = []
    for item in items:
        variant = variants[item.variant_id]
        if not available(variant) or item.quantity > variant.stock:
            raise Conflict('One or more items are unavailable.')
        subtotal += variant.price * item.quantity
        rows.append([item.pk, variant.pk, item.quantity, str(variant.price)])
    fee = Decimal(StoreSettings.load().shipping_fee).quantize(Decimal('0.01'))
    snapshot = shipping_address(user, data)
    quote = {'customer': user.pk, 'items': rows, 'shipping_fee': str(fee), 'address': snapshot}
    return quote, items, variants, subtotal, fee, snapshot


@transaction.atomic
def preview(user, data):
    cart = locked_cart(user)
    quote, items, variants, subtotal, fee, snapshot = quote_data(user, cart, data)
    return {'subtotal': str(subtotal), 'shipping_fee': str(fee), 'total': str(subtotal + fee),
            'address': snapshot, 'quote_token': signing.dumps(quote, salt='checkout', compress=True)}


@transaction.atomic
def checkout(user, data):
    if not data.get('idempotency_key') or not data.get('quote_token'):
        raise ValidationError('Preview the order and supply an idempotency key.')
    cart = locked_cart(user)
    request_hash = fingerprint(data)
    existing = Order.objects.filter(customer=user, idempotency_key=data['idempotency_key']).first()
    if existing:
        if existing.request_fingerprint != request_hash:
            raise Conflict('This idempotency key belongs to a different request.')
        return existing, False
    try:
        accepted_quote = signing.loads(data['quote_token'], salt='checkout', max_age=1800)
    except signing.BadSignature:
        raise Conflict('The quote expired. Preview and confirm again.')
    quote, items, variants, subtotal, fee, snapshot = quote_data(user, cart, data, lock=True)
    if accepted_quote != quote:
        raise Conflict('The price, cart or address changed. Preview and confirm again.')
    order = Order.objects.create(customer=user, subtotal=subtotal, shipping_fee=fee, total=subtotal + fee,
        address_snapshot=snapshot, comment=data.get('comment', ''), idempotency_key=data['idempotency_key'], request_fingerprint=request_hash)
    for item in items:
        variant = variants[item.variant_id]
        OrderItem.objects.create(order=order, variant=variant, product_name_snapshot={lang: getattr(variant.product, 'name_' + lang) for lang in ['uz', 'ru', 'en']},
            sku_snapshot=variant.sku, attributes_snapshot=variant.attributes, unit_price=variant.price, quantity=item.quantity, line_total=variant.price * item.quantity)
        move_stock(variant, -item.quantity, 'ORDER_OUT', user, 'Checkout', order)
    cart.items.filter(pk__in=[i.pk for i in items]).delete()
    OrderStatusHistory.objects.create(order=order, old_status='', new_status='NEW', actor=user)
    notify_admins('new_order', f'order:{order.pk}', f'/admin/orders/{order.public_number}/', number=order.public_number)
    return order, True


@transaction.atomic
def transition(actor, public_number, target, reason=''):
    qs = Order.objects.select_for_update()
    if actor.role != 'ADMIN':
        qs = qs.filter(customer=actor)
    order = get_object_or_404(qs, public_number=public_number)
    if order.status == 'CANCELLED' and target == 'CANCELLED':
        return order
    allowed = {'NEW': ['CONFIRMED', 'CANCELLED'], 'CONFIRMED': ['PACKING', 'CANCELLED'], 'PACKING': ['SHIPPED', 'CANCELLED'], 'SHIPPED': ['DELIVERED']}
    if actor.role != 'ADMIN' and not (order.status == 'NEW' and target == 'CANCELLED'):
        raise Conflict('Contact the store to change this order.')
    if target not in allowed.get(order.status, []):
        raise Conflict('This status transition is not allowed.')
    old = order.status
    if target == 'CANCELLED':
        items = {item.variant_id: item for item in order.items.all()}
        for variant in ProductVariant.objects.select_for_update().filter(pk__in=items).order_by('id'):
            move_stock(variant, items[variant.pk].quantity, 'CANCEL_RETURN', actor, reason or 'Order cancelled', order)
    order.status = target
    if target == 'DELIVERED':
        order.payment_status = 'PAID'
    order.save(update_fields=['status', 'payment_status', 'updated_at'])
    history = OrderStatusHistory.objects.create(order=order, old_status=old, new_status=target, actor=actor, reason=reason)
    notify(order.customer, 'order_status', f'order-status:{history.pk}', f'/shop/orders/{order.public_number}/', number=order.public_number, status=target)
    return order
