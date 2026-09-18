from django.test import TestCase
from apps.accounts.models import User


class PageAccessTests(TestCase):
    def test_guest_pages_and_private_redirect(self):
        for url in ['/', '/login/', '/register/', '/admin/login/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'id="sidebar"')
        self.assertRedirects(self.client.get('/shop/catalog/'), '/login/?next=%2Fshop%2Fcatalog%2F', fetch_redirect_response=False)

    def test_roles_and_private_cache(self):
        user = User.objects.create_user('a@example.com', 'Password239!')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/admin/dashboard/').status_code, 403)
        response = self.client.get('/shop/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertRedirects(self.client.get('/'), '/shop/')
        user.role = 'ADMIN'
        user.save()
        self.assertRedirects(self.client.get('/shop/'), '/admin/dashboard/')

    def test_languages_and_safe_redirect(self):
        for lang in ['uz', 'ru', 'en']:
            response = self.client.post('/language/', {'language': lang, 'next': 'https://evil.example'})
            self.assertEqual(response.url, '/')
            self.assertEqual(response.cookies['django_language'].value, lang)
            self.assertEqual(self.client.get('/api/v1/translations/').status_code, 200)
