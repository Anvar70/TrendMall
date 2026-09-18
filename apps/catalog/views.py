from decimal import Decimal, InvalidOperation
from django.db import IntegrityError, transaction
from django.db.models import Min, Q
from django.db.models.deletion import ProtectedError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from apps.accounts.permissions import IsAdmin
from apps.core.exceptions import Conflict
from .models import Category, Product, ProductVariant, ProductImage
from .serializers import CategorySerializer, ProductSerializer, VariantSerializer, ImageSerializer


def products():
    return Product.objects.select_related('category').prefetch_related('variants', 'images').annotate(min_price=Min('variants__price', filter=Q(variants__is_active=True)))


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(is_active=True)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        qs = products().filter(is_active=True, category__is_active=True, min_price__isnull=False)
        p = self.request.query_params
        if p.get('search'):
            term = p['search'][:150]
            qs = qs.filter(Q(name_uz__icontains=term) | Q(name_ru__icontains=term) | Q(name_en__icontains=term) | Q(variants__sku__icontains=term)).distinct()
        if p.get('category'):
            if not p['category'].isdigit():
                raise ValidationError({'category': 'Use a category ID.'})
            qs = qs.filter(category_id=p['category'])
        for param, lookup in [('min_price', 'min_price__gte'), ('max_price', 'min_price__lte')]:
            if p.get(param):
                try:
                    value = Decimal(p[param])
                    if not value.is_finite() or value < 0:
                        raise InvalidOperation
                    qs = qs.filter(**{lookup: value})
                except InvalidOperation:
                    raise ValidationError({param: 'Enter a non-negative price.'})
        if p.get('in_stock') == 'true':
            qs = qs.filter(variants__stock__gt=0, variants__is_active=True).distinct()
        if p.get('trending') == 'true':
            qs = qs.filter(is_trending=True)
        order = {'price': 'min_price', '-price': '-min_price', 'name': 'name_' + getattr(self.request, 'LANGUAGE_CODE', 'uz'), 'new': '-created_at'}.get(p.get('ordering'), '-created_at')
        return qs.order_by(order, 'id')


class AdminMutationMixin:
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise Conflict('A record with these unique fields already exists.')

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise Conflict('A record with these unique fields already exists.')

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise Conflict('This record has history. Archive it instead.')


class AdminCategoryViewSet(AdminMutationMixin, viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()


class AdminProductViewSet(AdminMutationMixin, viewsets.ModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        qs = products()
        if self.request.query_params.get('search'):
            qs = qs.filter(name_uz__icontains=self.request.query_params['search'])
        return qs


class AdminVariantViewSet(AdminMutationMixin, viewsets.ModelViewSet):
    serializer_class = VariantSerializer

    def get_queryset(self):
        qs = ProductVariant.objects.select_related('product').all()
        product = self.request.query_params.get('product')
        if product and product.isdigit():
            qs = qs.filter(product_id=product)
        return qs

    def perform_destroy(self, instance):
        if instance.product.variants.count() <= 1:
            raise Conflict('Keep at least one variant for the product.')
        super().perform_destroy(instance)


class AdminImageViewSet(AdminMutationMixin, viewsets.ModelViewSet):
    serializer_class = ImageSerializer
    queryset = ProductImage.objects.all()
