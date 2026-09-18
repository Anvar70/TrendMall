from django.conf import settings
from django.db import models


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=40)
    event_key = models.CharField(max_length=160)
    data = models.JSONField(default=dict)
    internal_target = models.CharField(max_length=200)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recipient', 'read_at'])]
        constraints = [models.UniqueConstraint(fields=['recipient', 'event_key'], name='unique_notification_event')]
