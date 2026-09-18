from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, AdminOrderViewSet, PreviewView
router = DefaultRouter()
router.register('orders', OrderViewSet, basename='order')
router.register('admin/orders', AdminOrderViewSet, basename='admin-order')
urlpatterns = [path('checkout/preview/', PreviewView.as_view())] + router.urls
