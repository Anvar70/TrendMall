from django.db.models import Q
from rest_framework import generics, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import IsAdmin
from .models import Order
from .serializers import CheckoutSerializer, OrderSerializer, TransitionSerializer
from .services import preview, checkout, transition


class PreviewView(generics.GenericAPIView):
    serializer_class = CheckoutSerializer

    def post(self, request):
        data = self.get_serializer(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(preview(request.user, data.validated_data))


def order_queryset():
    return Order.objects.select_related('customer').prefetch_related('items', 'history')


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    lookup_field = 'public_number'

    def get_queryset(self):
        return order_queryset().filter(customer=self.request.user)

    def create(self, request):
        data = CheckoutSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        order, created = checkout(request.user, data.validated_data)
        return Response(self.get_serializer(order).data, status=201 if created else 200)

    @action(detail=True, methods=['post'])
    def cancel(self, request, public_number=None):
        class Input(serializers.Serializer):
            reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
        data = Input(data=request.data)
        data.is_valid(raise_exception=True)
        order = transition(request.user, public_number, 'CANCELLED', data.validated_data['reason'])
        return Response(self.get_serializer(order).data)


class AdminOrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = OrderSerializer
    lookup_field = 'public_number'

    def get_queryset(self):
        from apps.core.filters import date_filter
        qs = order_queryset()
        p = self.request.query_params
        for key in ['status', 'payment_status']:
            if p.get(key):
                qs = qs.filter(**{key: p[key]})
        if p.get('search'):
            text = p['search'][:150]
            qs = qs.filter(Q(public_number__icontains=text) | Q(customer__full_name__icontains=text) | Q(customer__email__icontains=text) | Q(customer__phone__icontains=text))
        if p.get('customer') and p['customer'].isdigit():
            qs = qs.filter(customer_id=p['customer'])
        return date_filter(qs, p)

    @action(detail=True, methods=['post'], url_path='status')
    def change_status(self, request, public_number=None):
        data = TransitionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        order = transition(request.user, public_number, data.validated_data['status'], data.validated_data['reason'])
        return Response(self.get_serializer(order).data)
