from uuid import uuid4
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User, Address
from apps.catalog.models import Category, Product, ProductVariant
from apps.cart.services import change_cart
from apps.inventory.models import InventoryMovement
from apps.notifications.models import Notification
from .models import Order


class CheckoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('buyer@test.com', 'Password239!')
        self.admin = User.objects.create_user('admin@test.com', 'Password239!', role='ADMIN')
        self.client.force_authenticate(self.user)
        category = Category.objects.create(name_uz='Tech', slug='tech')
        product = Product.objects.create(category=category, name_uz='Lamp', slug='lamp', is_active=True)
        self.variant = ProductVariant.objects.create(product=product, sku='LAMP', price=50000, stock=10)
        self.address = Address.objects.create(user=self.user, label='Home', recipient_name='Buyer', phone='+998901234567', region='Tashkent', city='City', address_line='Street 1')
        change_cart(self.user, variant_id=self.variant.pk, quantity=2)

    def payload(self):
        data = {'address_id': self.address.pk}
        result = self.client.post('/api/v1/checkout/preview/', data, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        return {**data, 'quote_token': result.data['quote_token'], 'idempotency_key': str(uuid4())}

    def test_checkout_idempotency_and_notifications(self):
        payload = self.payload()
        first = self.client.post('/api/v1/orders/', payload, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data['total'], '125000.00')
        self.assertEqual(self.client.post('/api/v1/orders/', payload, format='json').status_code, 200)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 8)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(InventoryMovement.objects.filter(type='ORDER_OUT').count(), 1)
        self.assertEqual(Notification.objects.filter(type='new_order', recipient=self.admin).count(), 1)
        self.assertEqual(self.client.get('/api/v1/cart/').data['items'], [])
        changed = {**payload, 'comment': 'different request'}
        self.assertEqual(self.client.post('/api/v1/orders/', changed, format='json').status_code, 409)

    def test_changed_price_requires_new_confirmation_and_rollback(self):
        payload = self.payload()
        self.variant.price = 60000
        self.variant.save()
        self.assertEqual(self.client.post('/api/v1/orders/', payload, format='json').status_code, 409)
        self.assertFalse(Order.objects.exists())
        self.assertEqual(self.client.get('/api/v1/cart/').data['items'][0]['quantity'], 2)
        self.variant.stock = 1
        self.variant.save()
        self.assertEqual(self.client.post('/api/v1/checkout/preview/', {'address_id': self.address.pk}, format='json').status_code, 409)

    def test_cancel_once_and_snapshot_immutability(self):
        data = self.client.post('/api/v1/orders/', self.payload(), format='json').data
        self.address.address_line = 'Changed'
        self.address.save()
        self.variant.price = 999
        self.variant.save(update_fields=['price'])
        url = '/api/v1/orders/' + data['public_number'] + '/'
        for _ in range(2):
            self.assertEqual(self.client.post(url + 'cancel/', {}, format='json').status_code, 200)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)
        self.assertEqual(InventoryMovement.objects.filter(type='CANCEL_RETURN').count(), 1)
        order = self.client.get(url).data
        self.assertEqual(order['address_snapshot']['address_line'], 'Street 1')
        self.assertEqual(order['items'][0]['unit_price'], '50000.00')

    def test_transitions_payment_and_ownership(self):
        order = self.client.post('/api/v1/orders/', self.payload(), format='json').data
        other = User.objects.create_user('other@test.com', 'Password239!')
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get('/api/v1/orders/' + order['public_number'] + '/').status_code, 404)
        self.client.force_authenticate(self.admin)
        url = '/api/v1/admin/orders/' + order['public_number'] + '/status/'
        self.assertEqual(self.client.post(url, {'status': 'DELIVERED'}).status_code, 409)
        for status in ['CONFIRMED', 'PACKING', 'SHIPPED', 'DELIVERED']:
            response = self.client.post(url, {'status': status})
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['payment_status'], 'PAID')
        self.assertEqual(self.client.post(url, {'status': 'CANCELLED'}).status_code, 409)

    def test_customer_cannot_set_totals_and_notification_ownership(self):
        payload = self.payload()
        self.assertEqual(self.client.post('/api/v1/orders/', {**payload, 'total': '1'}, format='json').status_code, 400)
        self.client.post('/api/v1/orders/', payload, format='json')
        notification = Notification.objects.get(type='new_order')
        self.assertEqual(self.client.post(f'/api/v1/notifications/{notification.pk}/read/').status_code, 404)
