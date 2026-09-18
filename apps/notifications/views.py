from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import IsAdmin
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, url_path='unread-count')
    def unread_count(self, request):
        return Response({'count': self.get_queryset().filter(read_at__isnull=True).count()})

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        notification = self.get_object()
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=['read_at'])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        count = self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({'count': count})


class AdminNotificationViewSet(NotificationViewSet):
    permission_classes = [IsAdmin]
