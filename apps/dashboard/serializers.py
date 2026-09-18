from rest_framework import serializers
from apps.accounts.models import User
from apps.accounts.serializers import StrictSerializerMixin
from apps.core.models import StoreSettings


class CustomerSerializer(serializers.ModelSerializer):
    order_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone', 'date_joined', 'is_active', 'order_count']
        read_only_fields = fields


class ActiveSerializer(StrictSerializerMixin, serializers.Serializer):
    is_active = serializers.BooleanField()
    reason = serializers.CharField(max_length=500)


class StoreSettingsSerializer(StrictSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = '__all__'
        read_only_fields = ['id']
