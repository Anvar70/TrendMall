from django.test import TestCase
from rest_framework.test import APIClient
from .models import User


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.data = {'email': 'buyer@example.com', 'full_name': 'Buyer', 'phone': '+998901234567',
                     'password': 'Test-Password-239!', 'password_confirm': 'Test-Password-239!'}

    def csrf(self):
        return self.client.get('/api/v1/auth/csrf/').json()['csrfToken']

    def post(self, url, data):
        return self.client.post(url, data, format='json', HTTP_X_CSRFTOKEN=self.csrf())

    def test_anonymous_register_requires_csrf(self):
        response = self.client.post('/api/v1/auth/register/', self.data, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'csrf_failed')
        self.assertFalse(User.objects.exists())

    def test_register_rejects_role_and_logs_in_customer(self):
        bad = self.post('/api/v1/auth/register/', {**self.data, 'role': 'ADMIN'})
        self.assertEqual(bad.status_code, 400)
        response = self.post('/api/v1/auth/register/', self.data)
        self.assertEqual(response.status_code, 201)
        user = User.objects.get()
        self.assertEqual(user.role, 'CUSTOMER')
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password(self.data['password']))
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 200)

    def test_login_roles_redirect_and_deactivation(self):
        user = User.objects.create_user(self.data['email'], self.data['password'], full_name='Buyer', phone=self.data['phone'])
        data = {k: self.data[k] for k in ('email', 'password')}
        self.assertEqual(self.post('/api/v1/auth/admin-login/', data).status_code, 403)
        response = self.post('/api/v1/auth/login/', {**data, 'next': 'https://evil.example/'})
        self.assertEqual(response.json()['redirect'], '/shop/')
        user.is_active = False
        user.save()
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 403)

    def test_admin_cannot_use_customer_login(self):
        User.objects.create_user(self.data['email'], self.data['password'], role='ADMIN')
        data = {k: self.data[k] for k in ('email', 'password')}
        self.assertEqual(self.post('/api/v1/auth/login/', data).status_code, 403)
        self.assertEqual(self.post('/api/v1/auth/admin-login/', data).json()['redirect'], '/admin/dashboard/')

    def test_password_change_preserves_current_session_and_revokes_other(self):
        user = User.objects.create_user(self.data['email'], self.data['password'])
        self.client.force_login(user)
        other = APIClient()
        other.force_login(user)
        response = self.post('/api/v1/auth/change-password/', {'old_password': self.data['password'], 'new_password': 'New-Password-936!'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 200)
        self.assertEqual(other.get('/api/v1/auth/me/').status_code, 403)

    def test_email_case_insensitive(self):
        User.objects.create_user('BUYER@example.com', self.data['password'])
        response = self.post('/api/v1/auth/register/', self.data)
        self.assertEqual(response.status_code, 400)
