from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User, Address
from apps.catalog.models import Category, Product, ProductVariant
from .models import CartItem


class CustomerDataTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('buyer@test.com', 'Password239!')
        self.other = User.objects.create_user('other@test.com', 'Password239!')
        self.client.force_authenticate(self.user)
        category = Category.objects.create(name_uz='Tech', slug='tech')
        product = Product.objects.create(category=category, name_uz='Lamp', slug='lamp', is_active=True)
        self.variant = ProductVariant.objects.create(product=product, sku='LAMP', price=50, stock=5)

    def test_cart_persists_and_does_not_reserve_stock(self):
        url = '/api/v1/cart/items/'
        self.assertEqual(self.client.post(url, {'variant': self.variant.pk, 'quantity': 2}).status_code, 201)
        self.client.post(url, {'variant': self.variant.pk, 'quantity': 1})
        self.assertEqual(CartItem.objects.get().quantity, 3)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 5)
        self.client.force_authenticate(None)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get('/api/v1/cart/').data['subtotal'], '150.00')
        self.assertEqual(self.client.post(url, {'variant': self.variant.pk, 'quantity': 4}).status_code, 409)

    def test_cart_and_address_ownership(self):
        self.client.post('/api/v1/cart/items/', {'variant': self.variant.pk})
        item = CartItem.objects.get()
        address = Address.objects.create(user=self.user, label='Home', recipient_name='Buyer', phone='+998901234567', region='Tashkent', city='City', address_line='Street 1')
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.patch(f'/api/v1/cart/items/{item.pk}/', {'quantity': 1}).status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/addresses/{address.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/v1/addresses/{address.pk}/set-default/').status_code, 404)

    def test_default_address_is_unique_and_profile_protected(self):
        data = {'label': 'Home', 'recipient_name': 'Buyer', 'phone': '+998901234567', 'region': 'Tashkent', 'city': 'City', 'address_line': 'Street 1'}
        a = self.client.post('/api/v1/addresses/', data).data
        b = self.client.post('/api/v1/addresses/', {**data, 'label': 'Work', 'is_default': True}).data
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)
        self.assertEqual(Address.objects.get(is_default=True).pk, b['id'])
        self.assertEqual(self.client.patch('/api/v1/profile/', {'email': 'new@test.com'}).status_code, 400)
        self.assertEqual(self.client.patch('/api/v1/profile/', {'role': 'ADMIN'}).status_code, 400)

    def test_favorites_unique(self):
        for _ in range(2):
            self.client.post('/api/v1/favorites/', {'product': self.variant.product_id})
        self.assertEqual(self.client.get('/api/v1/favorites/').data['count'], 1)
