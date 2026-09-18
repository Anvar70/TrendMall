import json
from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from apps.accounts.serializers import StrictSerializerMixin
from .models import Category, Product, ProductVariant, ProductImage


def translated(obj, field, context):
    request = context.get('request')
    language = getattr(request, 'LANGUAGE_CODE', 'uz')
    return getattr(obj, f'{field}_{language}', '') or getattr(obj, f'{field}_uz', '')


class CategorySerializer(StrictSerializerMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'slug', 'name', 'name_uz', 'name_ru', 'name_en', 'image', 'sort_order', 'is_active']
        read_only_fields = ['id', 'name']

    def get_name(self, obj):
        return translated(obj, 'name', self.context)

    def validate(self, attrs):
        if attrs.get('is_active', getattr(self.instance, 'is_active', True)):
            for lang in ('uz', 'ru', 'en'):
                field = 'name_' + lang
                if not attrs.get(field, getattr(self.instance, field, '')):
                    raise serializers.ValidationError({field: 'Translation is required.'})
        return attrs


class VariantSerializer(StrictSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        exclude = ['canonical_attribute_key']
        read_only_fields = ['id', 'stock']
        validators = []

    def validate(self, attrs):
        attributes = attrs.get('attributes', getattr(self.instance, 'attributes', {}))
        if not isinstance(attributes, dict) or len(attributes) > 10:
            raise serializers.ValidationError({'attributes': 'Use an object with at most 10 attributes.'})
        canonical = {str(k).strip().lower(): str(v).strip().lower() for k, v in attributes.items()}
        key = json.dumps(canonical, sort_keys=True, ensure_ascii=True, separators=(',', ':'))
        if len(key) > 500:
            raise serializers.ValidationError({'attributes': 'Attributes are too long.'})
        product = attrs.get('product', getattr(self.instance, 'product', None))
        if self.instance and product != self.instance.product:
            raise serializers.ValidationError({'product': 'A variant cannot be moved to another product.'})
        others = ProductVariant.objects.filter(product=product, canonical_attribute_key=key)
        if self.instance:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            raise serializers.ValidationError({'attributes': 'This combination already exists.'})
        price = attrs.get('price', getattr(self.instance, 'price', Decimal('0')))
        old = attrs.get('compare_at_price', getattr(self.instance, 'compare_at_price', None))
        if old is not None and old <= price:
            raise serializers.ValidationError({'compare_at_price': 'Old price must exceed current price.'})
        attrs['attributes'] = canonical
        return attrs


class ImageSerializer(StrictSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'
        read_only_fields = ['id']


class ProductSerializer(StrictSerializerMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    variants = VariantSerializer(many=True, read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    min_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    default_price = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'), write_only=True, required=False)

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_name(self, obj):
        return translated(obj, 'name', self.context)

    def get_description(self, obj):
        return translated(obj, 'description', self.context)

    def get_short_description(self, obj):
        return translated(obj, 'short_description', self.context)

    def get_category_name(self, obj):
        return translated(obj.category, 'name', self.context)

    def validate(self, attrs):
        if not self.instance and 'default_price' not in attrs:
            raise serializers.ValidationError({'default_price': 'Default variant price is required.'})
        if self.instance and 'default_price' in attrs:
            raise serializers.ValidationError({'default_price': 'Edit price through variants.'})
        if attrs.get('is_active', getattr(self.instance, 'is_active', False)):
            for lang in ('uz', 'ru', 'en'):
                for key in ('name', 'short_description', 'description'):
                    field = key + '_' + lang
                    if not attrs.get(field, getattr(self.instance, field, '')):
                        raise serializers.ValidationError({field: 'Complete translations before publishing.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        price = validated_data.pop('default_price')
        product = super().create(validated_data)
        ProductVariant.objects.create(product=product, sku=f'TB-{product.pk}-DEFAULT', price=price)
        return product

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.role != 'ADMIN':
            data['variants'] = [v for v in data['variants'] if v['is_active']]
        return data
