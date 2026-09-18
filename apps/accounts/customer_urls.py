from django.urls import path
from rest_framework.routers import DefaultRouter
from .customer_views import ProfileView, SettingsView, AddressViewSet
router = DefaultRouter()
router.register('addresses', AddressViewSet, basename='address')
urlpatterns = [path('profile/', ProfileView.as_view()), path('settings/', SettingsView.as_view())] + router.urls
