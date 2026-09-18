from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.catalog.models import Product
from apps.catalog.views import products
from .models import Favorite
from .serializers import CartMutationSerializer, FavoriteSerializer
from .services import change_cart, cart_data


class CartView(APIView):
    def get(self, request):
        return Response(cart_data(request.user, {'request': request}))


class CartItemsView(generics.GenericAPIView):
    serializer_class = CartMutationSerializer

    def post(self, request):
        data = self.get_serializer(data=request.data)
        data.is_valid(raise_exception=True)
        if not data.validated_data.get('variant'):
            raise serializers.ValidationError({'variant': 'Choose a variant.'})
        change_cart(request.user, variant_id=data.validated_data['variant'], quantity=data.validated_data['quantity'])
        return Response(cart_data(request.user, {'request': request}), status=201)

    def patch(self, request, pk):
        data = self.get_serializer(data=request.data)
        data.is_valid(raise_exception=True)
        if 'variant' in data.validated_data:
            raise serializers.ValidationError({'variant': 'The variant cannot be changed.'})
        change_cart(request.user, item_id=pk, quantity=data.validated_data['quantity'])
        return Response(cart_data(request.user, {'request': request}))

    def delete(self, request, pk):
        change_cart(request.user, item_id=pk, remove=True)
        return Response(status=204)


class FavoritesView(generics.ListAPIView):
    serializer_class = FavoriteSerializer

    def get_queryset(self):
        from django.db.models import Prefetch
        return Favorite.objects.filter(user=self.request.user).prefetch_related(Prefetch('product', queryset=products()))

    def post(self, request):
        class Input(serializers.Serializer):
            product = serializers.IntegerField(min_value=1)
        data = Input(data=request.data)
        data.is_valid(raise_exception=True)
        product = get_object_or_404(Product, pk=data.validated_data['product'], is_active=True, category__is_active=True)
        favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)
        return Response({'id': favorite.pk}, status=201 if created else 200)

    def delete(self, request, product_id):
        favorite = get_object_or_404(Favorite, user=request.user, product_id=product_id)
        favorite.delete()
        return Response(status=204)
