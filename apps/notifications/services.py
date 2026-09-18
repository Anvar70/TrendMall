from apps.accounts.models import User
from .models import Notification


def notify(recipient, kind, event, target, **data):
    Notification.objects.get_or_create(recipient=recipient, event_key=event, defaults={'type': kind, 'internal_target': target, 'data': data})


def notify_admins(kind, event, target, **data):
    for admin in User.objects.filter(role='ADMIN', is_active=True):
        notify(admin, kind, event, target, **data)
