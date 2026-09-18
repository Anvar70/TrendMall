from uuid import uuid4
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.orders.models import Order
from apps.core.models import AuditLog


class DashboardTests(TestCase):
    def test_revenue_only_delivered_paid_and_customer_deactivation(self):
        client = APIClient()
        admin = User.objects.create_user('admin@test.com', 'Password239!', role='ADMIN')
        customer = User.objects.create_user('buyer@test.com', 'Password239!')
        for status, paid in [('NEW', 'UNPAID'), ('CANCELLED', 'UNPAID'), ('DELIVERED', 'PAID')]:
            Order.objects.create(customer=customer, status=status, payment_status=paid, subtotal=100, shipping_fee=0, total=100, address_snapshot={}, idempotency_key=uuid4(), request_fingerprint='test')
        client.force_authenticate(admin)
        response = client.get('/api/v1/admin/dashboard/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['revenue'], '100')
        self.assertEqual(response.data['total_orders'], 3)
        response = client.post(f'/api/v1/admin/customers/{customer.pk}/set-active/', {'is_active': False, 'reason': 'Requested by customer'})
        self.assertEqual(response.status_code, 200)
        customer.refresh_from_db()
        self.assertFalse(customer.is_active)
        self.assertTrue(AuditLog.objects.filter(action='customer_active').exists())
