from django.db import transaction
from django.utils import timezone
from apps.notifications.services import notify, notify_admins
from .models import Message


@transaction.atomic
def send_message(conversation, sender, body):
    message = Message.objects.create(conversation=conversation, sender=sender, body=body)
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=['updated_at'])
    if sender.role == 'CUSTOMER':
        notify_admins('customer_message', f'message:{message.pk}', f'/admin/messages/?conversation={conversation.pk}', customer=sender.full_name)
    else:
        notify(conversation.customer, 'admin_reply', f'message:{message.pk}', '/shop/messages/')
    return message
