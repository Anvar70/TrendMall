from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from uuid import uuid4
from django.db import connection, connections, close_old_connections
from django.test import TransactionTestCase
from apps.accounts.models import User, Address
from apps.catalog.models import Category, Product, ProductVariant
from apps.cart.services import change_cart
from apps.core.exceptions import Conflict
from apps.core.models import StoreSettings
from apps.inventory.models import InventoryMovement
from .models import Order
from .services import preview, checkout, transition


@skipUnless(connection.vendor == 'postgresql', 'Requires real PostgreSQL row locks.')
class PostgreSQLConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        StoreSettings.load()
        self.users = [User.objects.create_user(f'buyer{n}@test.com', 'Concurrency-Test-394!') for n in range(2)]
        category = Category.objects.create(slug='test', name_uz='Test')
        product = Product.objects.create(category=category, slug='test', name_uz='Test', is_active=True)
        self.variant = ProductVariant.objects.create(product=product, sku='LAST-ONE', price=100, stock=1)
        self.payloads = []
        for user in self.users:
            address = Address.objects.create(user=user, label='Home', recipient_name='Buyer', phone='+998901234567',
                region='Tashkent', city='City', address_line='Test street')
            change_cart(user, variant_id=self.variant.pk, quantity=1)
            data = {'address_id': address.pk}
            self.payloads.append({**data, 'quote_token': preview(user, data)['quote_token'], 'idempotency_key': uuid4()})

    def parallel(self, calls):
        barrier = Barrier(len(calls))
        def run(call):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '10s'")
                    cursor.execute("SET statement_timeout = '20s'")
                barrier.wait(timeout=10)
                try:
                    return call()
                except Conflict:
                    return 'conflict'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            futures = [pool.submit(run, call) for call in calls]
            return [future.result(timeout=30) for future in futures]

    def test_last_item_only_one_customer_succeeds(self):
        results = self.parallel([
            lambda: checkout(User.objects.get(pk=self.users[0].pk), self.payloads[0])[0].pk,
            lambda: checkout(User.objects.get(pk=self.users[1].pk), self.payloads[1])[0].pk,
        ])
        self.assertEqual(results.count('conflict'), 1, results)
        self.assertEqual(Order.objects.count(), 1)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 0)
        self.assertEqual(InventoryMovement.objects.filter(type='ORDER_OUT').count(), 1)

    def test_same_key_parallel_retry_creates_one_order(self):
        def submit():
            return checkout(User.objects.get(pk=self.users[0].pk), self.payloads[0])[0].pk
        results = self.parallel([submit, submit])
        self.assertEqual(results[0], results[1])
        self.assertNotEqual(results[0], 'conflict')
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(InventoryMovement.objects.filter(type='ORDER_OUT').count(), 1)

    def test_parallel_cancel_restores_stock_once(self):
        order, _ = checkout(self.users[0], self.payloads[0])
        def cancel():
            return transition(User.objects.get(pk=self.users[0].pk), order.public_number, 'CANCELLED').pk
        results = self.parallel([cancel, cancel])
        self.assertEqual(results, [order.pk, order.pk])
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 1)
        self.assertEqual(InventoryMovement.objects.filter(type='CANCEL_RETURN').count(), 1)

