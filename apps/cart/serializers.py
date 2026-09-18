from rest_framework import serializers
from apps.accounts.serializers import StrictSerializerMixin
from apps.catalog.serializers import translated, ProductSerializer
from .models import CartItem, Favorite


class CartItemSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    price = serializers.DecimalField(source='variant.price', max_digits=14, decimal_places=2, read_only=True)
    stock = serializers.IntegerField(source='variant.stock', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    attributes = serializers.JSONField(source='variant.attributes', read_only=True)
    slug = serializers.CharField(source='variant.product.slug', read_only=True)
    line_total = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    price_changed = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'variant', 'name', 'image', 'price', 'stock', 'sku', 'attributes', 'slug', 'quantity', 'line_total', 'available', 'price_changed']

    def get_name(self, obj):
        return translated(obj.variant.product, 'name', self.context)

    def get_image(self, obj):
        image = obj.variant.image
        if not image:
            first = next(iter(obj.variant.product.images.all()), None)
            image = first.image if first else None
        return image.url if image else None

    def get_line_total(self, obj):
        return str(obj.variant.price * obj.quantity)

    def get_available(self, obj):
        from .services import available
        return available(obj.variant) and obj.quantity <= obj.variant.stock

    def get_price_changed(self, obj):
        return obj.added_price != obj.variant.price


class CartMutationSerializer(StrictSerializerMixin, serializers.Serializer):
    variant = serializers.IntegerField(min_value=1, required=False)
    quantity = serializers.IntegerField(min_value=1, max_value=10000, default=1)


class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'product']
