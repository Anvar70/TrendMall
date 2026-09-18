from rest_framework import serializers
from apps.accounts.serializers import StrictSerializerMixin
from .models import InventoryMovement


class MovementSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source='variant.sku', read_only=True)

    class Meta:
        model = InventoryMovement
        fields = '__all__'


class AdjustmentSerializer(StrictSerializerMixin, serializers.Serializer):
    delta = serializers.IntegerField(min_value=-1000000, max_value=1000000)
    reason = serializers.CharField(max_length=500)
    type = serializers.ChoiceField(choices=['INITIAL', 'RESTOCK', 'ADJUSTMENT'], default='ADJUSTMENT')

    def validate(self, attrs):
        if not attrs['delta'] or (attrs['type'] in ['INITIAL', 'RESTOCK'] and attrs['delta'] < 1):
            raise serializers.ValidationError({'delta': 'Use a nonzero adjustment or positive restock.'})
        return attrs
