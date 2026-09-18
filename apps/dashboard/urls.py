from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CustomersViewSet, StoreSettingsView, PublicStoreView, DashboardView
router = DefaultRouter()
router.register('admin/customers', CustomersViewSet, basename='admin-customer')
urlpatterns = [path('admin/dashboard/', DashboardView.as_view()), path('admin/store-settings/', StoreSettingsView.as_view()),
    path('store/', PublicStoreView.as_view())] + router.urls
