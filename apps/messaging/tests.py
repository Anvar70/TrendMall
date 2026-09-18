from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.notifications.models import Notification
from .models import Conversation, Message


class MessagingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user('buyer@test.com', 'Password239!')
        self.admin = User.objects.create_user('admin@test.com', 'Password239!', role='ADMIN')
        self.client.force_authenticate(self.customer)

    def test_two_way_messages_read_and_incremental_poll(self):
        response = self.client.post('/api/v1/conversation/messages/', {'body': '<script>alert(1)</script>'})
        self.assertEqual(response.status_code, 201)
        first = response.data['id']
        conversation = Conversation.objects.get()
        self.assertEqual(Notification.objects.filter(recipient=self.admin).count(), 1)
        self.client.force_authenticate(self.admin)
        prefix = f'/api/v1/admin/conversations/{conversation.pk}/'
        self.assertEqual(self.client.get('/api/v1/admin/conversations/').data['results'][0]['unread_count'], 1)
        self.client.post(prefix + 'read/', {'last_seen_message_id': first})
        self.assertIsNotNone(Message.objects.get(pk=first).read_at)
        response = self.client.post(prefix + 'messages/', {'body': 'We can help.'})
        self.assertEqual(response.status_code, 201)
        self.client.force_authenticate(self.customer)
        messages = self.client.get(f'/api/v1/conversation/messages/?after_id={first}').data['results']
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['sender_role'], 'ADMIN')
        self.assertEqual(Notification.objects.filter(recipient=self.customer).count(), 1)

    def test_message_limits_protected_fields_and_ownership(self):
        self.assertEqual(self.client.post('/api/v1/conversation/messages/', {'body': ' '}).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/conversation/messages/', {'body': 'x' * 2001}).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/conversation/messages/', {'body': 'Hi', 'sender': self.admin.pk}).status_code, 400)
        other = User.objects.create_user('other@test.com', 'Password239!')
        conversation = Conversation.objects.create(customer=other)
        message = Message.objects.create(conversation=conversation, sender=self.admin, body='Private')
        self.assertEqual(self.client.post('/api/v1/conversation/read/', {'last_seen_message_id': message.pk}).status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/admin/conversations/{conversation.pk}/messages/').status_code, 403)
