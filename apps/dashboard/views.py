from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Count, Sum, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import generics, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin
from apps.catalog.models import Product, ProductVariant
from apps.core.models import StoreSettings, AuditLog
from apps.core.filters import date_filter
from apps.orders.models import Order
from apps.orders.views import order_queryset
from apps.orders.serializers import OrderSerializer
from apps.catalog.serializers import VariantSerializer
from apps.messaging.models import Message
from .serializers import CustomerSerializer, ActiveSerializer, StoreSettingsSerializer


class CustomersViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = CustomerSerializer

    def get_queryset(self):
        qs = User.objects.filter(role='CUSTOMER').annotate(order_count=Count('orders')).order_by('-date_joined')
        text = self.request.query_params.get('search')
        if text:
            qs = qs.filter(Q(full_name__icontains=text) | Q(email__icontains=text) | Q(phone__icontains=text))
        return qs

    @action(detail=True, methods=['post'], url_path='set-active')
    @transaction.atomic
    def set_active(self, request, pk=None):
        customer = self.get_object()
        data = ActiveSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        customer.is_active = data.validated_data['is_active']
        customer.save(update_fields=['is_active'])
        AuditLog.objects.create(actor=request.user, action='customer_active', entity_type='User', entity_id=str(customer.pk), details=data.validated_data)
        return Response(self.get_serializer(customer).data)


class StoreSettingsView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdmin]
    serializer_class = StoreSettingsSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return StoreSettings.load()

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(actor=self.request.user, action='store_settings', entity_type='StoreSettings', entity_id='1', details={'fields': list(serializer.validated_data)})


class PublicStoreView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        settings = StoreSettings.load()
        return Response({key: getattr(settings, key) for key in ['name', 'landing_uz', 'landing_ru', 'landing_en', 'support_phone', 'support_email']})


class DashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        orders = date_filter(Order.objects.all(), request.query_params)
        revenue = orders.filter(status='DELIVERED', payment_status='PAID').aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        days = 7 if request.query_params.get('days') == '7' else 30
        start = timezone.localdate() - timedelta(days=days-1)
        series = orders.filter(created_at__date__gte=start).annotate(day=TruncDate('created_at')).values('day').annotate(
            orders=Count('id'), revenue=Sum('total', filter=Q(status='DELIVERED', payment_status='PAID'))).order_by('day')
        data = {row['day']: row for row in series}
        chart = []
        for offset in range(days):
            day = start + timedelta(days=offset)
            row = data.get(day, {})
            chart.append({'date': day.isoformat(), 'orders': row.get('orders', 0), 'revenue': str(row.get('revenue') or Decimal('0.00'))})
        low_stock = ProductVariant.objects.filter(is_active=True, stock__lte=F('low_stock_threshold'))
        return Response({'total_orders': orders.count(), 'new_orders': orders.filter(status='NEW').count(),
            'active_customers': User.objects.filter(role='CUSTOMER', is_active=True).count(),
            'active_products': Product.objects.filter(is_active=True, category__is_active=True).count(),
            'low_stock_count': low_stock.count(), 'revenue': str(revenue), 'chart': chart,
            'unread_messages': Message.objects.filter(sender__role='CUSTOMER', read_at__isnull=True).count(),
            'recent_orders': OrderSerializer(date_filter(order_queryset(), request.query_params)[:5], many=True).data,
            'low_stock': VariantSerializer(low_stock[:5], many=True).data})
