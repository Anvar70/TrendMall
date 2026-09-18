from rest_framework import serializers
from apps.accounts.models import phone_validator
from apps.accounts.serializers import StrictSerializerMixin
from .models import Order, OrderItem, OrderStatusHistory


class ShippingAddressSerializer(StrictSerializerMixin, serializers.Serializer):
    recipient_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(validators=[phone_validator])
    region = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=100)
    address_line = serializers.CharField(max_length=300)
    landmark = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')


class CheckoutSerializer(StrictSerializerMixin, serializers.Serializer):
    address_id = serializers.IntegerField(min_value=1, required=False)
    address = ShippingAddressSerializer(required=False)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True, default='')
    idempotency_key = serializers.UUIDField(required=False)
    quote_token = serializers.CharField(required=False, max_length=10000)

    def validate(self, attrs):
        if ('address_id' in attrs) == ('address' in attrs):
            raise serializers.ValidationError('Choose an address or supply a new one.')
        return attrs


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name_snapshot', 'sku_snapshot', 'attributes_snapshot', 'unit_price', 'quantity', 'line_total']


class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ['old_status', 'new_status', 'reason', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    history = HistorySerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)

    class Meta:
        model = Order
        exclude = ['request_fingerprint', 'idempotency_key']
        read_only_fields = ['status', 'payment_status']


class TransitionSerializer(StrictSerializerMixin, serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
