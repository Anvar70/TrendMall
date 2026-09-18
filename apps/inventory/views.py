from rest_framework import generics
from rest_framework.response import Response
from apps.accounts.permissions import IsAdmin
from apps.catalog.models import ProductVariant
from apps.catalog.serializers import VariantSerializer
from .models import InventoryMovement
from .serializers import MovementSerializer, AdjustmentSerializer
from .services import adjust_stock


class InventoryView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = VariantSerializer
    queryset = ProductVariant.objects.select_related('product').all()


class MovementView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = MovementSerializer
    queryset = InventoryMovement.objects.select_related('variant').all()


class AdjustmentView(generics.GenericAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdjustmentSerializer

    def post(self, request, variant_id):
        data = self.get_serializer(data=request.data)
        data.is_valid(raise_exception=True)
        value = data.validated_data
        movement = adjust_stock(request.user, variant_id, value['delta'], value['reason'], value['type'])
        return Response(MovementSerializer(movement).data, status=201)
