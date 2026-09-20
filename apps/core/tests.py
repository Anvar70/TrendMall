import os
import tempfile
from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.catalog.models import Product, ProductVariant, ProductImage
from apps.inventory.models import InventoryMovement
from apps.orders.models import Order
from apps.messaging.models import Conversation, Message


class DemoIntegrationTests(TestCase):
    def test_seed_is_idempotent_and_full_customer_admin_flow(self):
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media, DEBUG=True), patch.dict(os.environ, {
                'DEMO_ADMIN_PASSWORD': 'Demo-Admin-Test-849!',
                'DEMO_CUSTOMER_PASSWORD': 'Demo-Customer-Test-849!',
            }):
                call_command('seed_demo', stdout=StringIO())
                counts = [model.objects.count() for model in [User, Product, ProductVariant, ProductImage, Order, InventoryMovement, Conversation, Message]]
                call_command('seed_demo', stdout=StringIO())
                self.assertEqual(counts, [model.objects.count() for model in [User, Product, ProductVariant, ProductImage, Order, InventoryMovement, Conversation, Message]])
                self.assertEqual(Product.objects.count(), 24)
                self.assertEqual(ProductVariant.objects.count(), 48)
                for variant in ProductVariant.objects.all():
                    self.assertEqual(variant.stock, sum(variant.movements.values_list('delta', flat=True)))
                client = APIClient(enforce_csrf_checks=True)
                def post(url, data):
                    token = client.get('/api/v1/auth/csrf/').data['csrfToken']
                    return client.post(url, data, format='json', HTTP_X_CSRFTOKEN=token)
                response = post('/api/v1/auth/register/', {
                    'email': 'journey@example.com', 'full_name': 'Journey Test', 'phone': '+998901234567',
                    'password': 'Journey-Password-394!', 'password_confirm': 'Journey-Password-394!',
                })
                self.assertEqual(response.status_code, 201, response.data)
                response = client.get('/api/v1/products/?in_stock=true')
                self.assertEqual(response.status_code, 200)
                product = response.data['results'][0]
                variant = next(v for v in product['variants'] if v['stock'] > 0)
                self.assertEqual(post('/api/v1/cart/items/', {'variant': variant['id'], 'quantity': 1}).status_code, 201)
                address = {'recipient_name': 'Journey Test', 'phone': '+998901234567', 'region': 'Tashkent', 'city': 'City', 'address_line': 'Test street'}
                quote = post('/api/v1/checkout/preview/', {'address': address})
                self.assertEqual(quote.status_code, 200, quote.data)
                from uuid import uuid4
                order = post('/api/v1/orders/', {'address': address, 'quote_token': quote.data['quote_token'], 'idempotency_key': str(uuid4())})
                self.assertEqual(order.status_code, 201, order.data)
                self.assertEqual(post('/api/v1/conversation/messages/', {'body': 'My order: ' + order.data['public_number']}).status_code, 201)
                buyer = User.objects.get(email='journey@example.com')
                self.assertEqual(post('/api/v1/auth/logout/', {}).status_code, 200)
                self.assertEqual(post('/api/v1/auth/admin-login/', {'email': 'admin@trendbox.local', 'password': 'Demo-Admin-Test-849!'}).status_code, 200)
                self.assertEqual(client.get('/api/v1/admin/orders/' + order.data['public_number'] + '/').status_code, 200)
                conversation = buyer.conversation
                self.assertEqual(post(f'/api/v1/admin/conversations/{conversation.pk}/messages/', {'body': 'Your order is being prepared.'}).status_code, 201)
                self.assertTrue(buyer.notifications.filter(type='admin_reply').exists())
                for language in ['uz', 'ru', 'en']:
                    client.cookies['django_language'] = language
                    response = client.get('/admin/dashboard/')
                    self.assertContains(response, f'lang="{language}"')
                    self.assertContains(response, '/static/js/admin.js')
