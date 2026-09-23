from io import BytesIO
import tempfile
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.catalog.models import Category, Product, ProductVariant
from apps.core.models import StoreSettings
from apps.inventory.services import adjust_stock
from apps.notifications.models import Notification


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SecurityRegressionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user('buyer@security.test', 'Security-Test-239!', full_name='Buyer', phone='+998901234567')
        self.admin = User.objects.create_user('admin@security.test', 'Security-Test-239!', role='ADMIN')
        self.category = Category.objects.create(slug='secure', name_uz='Secure', name_ru='Secure', name_en='Secure')
        self.product = Product.objects.create(category=self.category, slug='secure', name_uz='Secure', is_active=True)
        self.variant = ProductVariant.objects.create(product=self.product, sku='SECURE', price=100, stock=10, low_stock_threshold=5)

    def test_superuser_customer_cannot_bypass_admin_role(self):
        self.customer.is_superuser = True
        self.customer.is_staff = True
        self.customer.save()
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get('/api/v1/admin/dashboard/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/customers/').status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/v1/products/').status_code, 403)

    def test_invalid_and_normalized_phone(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.patch('/api/v1/profile/', {'phone': 'wrong'}).status_code, 400)
        response = self.client.patch('/api/v1/profile/', {'phone': '998 90 123 45 67'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['phone'], '+998901234567')

    def test_upload_validation_and_random_filename(self):
        self.client.force_authenticate(self.customer)
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            bad = SimpleUploadedFile('attack.svg', b'<svg onload="alert(1)"></svg>', content_type='image/svg+xml')
            self.assertEqual(self.client.patch('/api/v1/profile/', {'avatar': bad}, format='multipart').status_code, 400)
            fake = SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')
            self.assertEqual(self.client.patch('/api/v1/profile/', {'avatar': fake}, format='multipart').status_code, 400)
            buffer = BytesIO()
            Image.new('RGB', (20, 20), 'orange').save(buffer, format='PNG')
            good = SimpleUploadedFile('private-original-name.png', buffer.getvalue(), content_type='image/png')
            response = self.client.patch('/api/v1/profile/', {'avatar': good}, format='multipart')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertNotIn('private-original-name', response.data['avatar'])

    def test_oversized_image_and_dimensions_rejected(self):
        self.client.force_authenticate(self.customer)
        buffer = BytesIO()
        Image.new('RGB', (10, 10)).save(buffer, format='PNG')
        huge = SimpleUploadedFile('large.png', buffer.getvalue() + bytes(5 * 1024 * 1024), content_type='image/png')
        self.assertEqual(self.client.patch('/api/v1/profile/', {'avatar': huge}, format='multipart').status_code, 400)
        buffer = BytesIO()
        Image.new('RGB', (8001, 1)).save(buffer, format='PNG')
        wide = SimpleUploadedFile('wide.png', buffer.getvalue(), content_type='image/png')
        self.assertEqual(self.client.patch('/api/v1/profile/', {'avatar': wide}, format='multipart').status_code, 400)

    def test_low_stock_notification_only_on_threshold_crossing(self):
        adjust_stock(self.admin, self.variant.pk, -5, 'Threshold')
        adjust_stock(self.admin, self.variant.pk, -1, 'Still low')
        self.assertEqual(Notification.objects.filter(type='low_stock').count(), 1)
        adjust_stock(self.admin, self.variant.pk, 10, 'Restock', 'RESTOCK')
        adjust_stock(self.admin, self.variant.pk, -10, 'Another crossing')
        self.assertEqual(Notification.objects.filter(type='low_stock').count(), 2)

    def test_negative_stock_adjustment_rolls_back(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/api/v1/admin/inventory/{self.variant.pk}/adjust/', {'delta': -11, 'reason': 'Invalid', 'type': 'ADJUSTMENT'})
        self.assertEqual(response.status_code, 409)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)
        self.assertFalse(self.variant.movements.exists())

    def test_wrong_http_methods_return_405_not_500(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.patch('/api/v1/cart/items/', {'quantity': 1}).status_code, 405)
        self.assertEqual(self.client.post('/api/v1/cart/items/1/', {'variant': 1}).status_code, 405)
        self.assertEqual(self.client.get('/api/v1/favorites/1/').status_code, 405)
        self.assertEqual(self.client.delete('/api/v1/favorites/').status_code, 405)

    def test_three_language_errors(self):
        self.client.force_authenticate(self.customer)
        responses = []
        for language in ['uz', 'ru', 'en']:
            self.client.cookies['django_language'] = language
            response = self.client.patch('/api/v1/profile/', {'email': 'forbidden@security.test'})
            self.assertEqual(response.status_code, 400)
            responses.append(response.data['field_errors']['email'][0])
        self.assertEqual(len(set(responses)), 3)

    def test_schema_hidden_from_guest_and_customer_in_production(self):
        with override_settings(DEBUG=False):
            self.assertEqual(self.client.get('/api/schema/').status_code, 403)
            self.client.force_authenticate(self.customer)
            self.assertEqual(self.client.get('/api/docs/').status_code, 403)
            self.client.force_authenticate(self.admin)
            self.assertEqual(self.client.get('/api/schema/').status_code, 200)

    def test_default_inventory_threshold_comes_from_store_settings(self):
        store = StoreSettings.load()
        store.default_low_stock_threshold = 8
        store.save()
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/v1/admin/products/', {'category': self.category.pk, 'slug': 'new-draft', 'name_uz': 'Draft', 'default_price': '200.00'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(ProductVariant.objects.get(product_id=response.data['id']).low_stock_threshold, 8)

    def test_admin_gallery_keeps_one_primary_image(self):
        from apps.catalog.models import ProductImage
        self.client.force_authenticate(self.admin)
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            ids = []
            for index in range(2):
                buffer = BytesIO()
                Image.new('RGB', (20, 20), 'orange').save(buffer, format='PNG')
                uploaded = SimpleUploadedFile(f'image{index}.png', buffer.getvalue(), content_type='image/png')
                response = self.client.post('/api/v1/admin/images/', {'product': self.product.pk, 'image': uploaded, 'is_primary': True}, format='multipart')
                self.assertEqual(response.status_code, 201, response.data)
                ids.append(response.data['id'])
            self.assertEqual(ProductImage.objects.filter(product=self.product, is_primary=True).count(), 1)
            self.assertEqual(ProductImage.objects.get(is_primary=True).pk, ids[1])
            response = self.client.patch(f'/api/v1/admin/images/{ids[0]}/', {'is_primary': True}, format='json')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(ProductImage.objects.get(is_primary=True).pk, ids[0])
