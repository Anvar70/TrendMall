from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, AdminNotificationViewSet
router = DefaultRouter()
router.register('notifications', NotificationViewSet, basename='notification')
router.register('admin/notifications', AdminNotificationViewSet, basename='admin-notification')
urlpatterns = router.urls
