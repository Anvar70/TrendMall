from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from .models import Category, Product, ProductVariant


class CatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user('admin@test.com', 'Password239!', role='ADMIN')
        self.customer = User.objects.create_user('customer@test.com', 'Password239!')
        self.category = Category.objects.create(name_uz='Tech', name_ru='Tech', name_en='Tech', slug='tech')

    def test_guest_and_customer_cannot_mutate(self):
        self.assertEqual(self.client.get('/api/v1/products/').status_code, 403)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.post('/api/v1/admin/products/', {}).status_code, 403)

    def test_product_requires_translations_and_creates_default_variant(self):
        self.client.force_authenticate(self.admin)
        data = {'category': self.category.pk, 'slug': 'lamp', 'name_uz': 'Lamp', 'default_price': '50000.00', 'is_active': True}
        self.assertEqual(self.client.post('/api/v1/admin/products/', data).status_code, 400)
        data['is_active'] = False
        response = self.client.post('/api/v1/admin/products/', data)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(ProductVariant.objects.get().price, 50000)
        self.assertEqual(ProductVariant.objects.get().stock, 0)

    def test_price_filter_uses_minimum_active_variant(self):
        product = Product.objects.create(category=self.category, name_uz='Lamp', slug='lamp', is_active=True)
        ProductVariant.objects.create(product=product, sku='A', price=50)
        ProductVariant.objects.create(product=product, sku='B', price=100, attributes={'color': 'white'})
        ProductVariant.objects.create(product=product, sku='C', price=1, attributes={'color': 'red'}, is_active=False)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get('/api/v1/products/?min_price=75').data['count'], 0)
        response = self.client.get('/api/v1/products/?max_price=75')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['min_price'], '50.00')
        self.assertEqual(len(response.data['results'][0]['variants']), 2)

    def test_variant_rejects_stock_write_and_duplicate_attributes(self):
        product = Product.objects.create(category=self.category, name_uz='Lamp', slug='lamp')
        ProductVariant.objects.create(product=product, sku='A', price=50, attributes={'color': 'red'})
        self.client.force_authenticate(self.admin)
        data = {'product': product.pk, 'sku': 'B', 'price': '50.00', 'attributes': {'Color': ' RED '}}
        self.assertEqual(self.client.post('/api/v1/admin/variants/', data, format='json').status_code, 400)
        self.assertEqual(self.client.patch('/api/v1/admin/variants/1/', {'stock': 99}, format='json').status_code, 400)
