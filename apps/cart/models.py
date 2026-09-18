from django.conf import settings
from django.db import models


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_price = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['cart', 'variant'], name='unique_cart_variant'),
                       models.CheckConstraint(condition=models.Q(quantity__gt=0), name='cart_quantity_positive')]


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE)

    class Meta:
        ordering = ['-id']
        constraints = [models.UniqueConstraint(fields=['user', 'product'], name='unique_user_favorite')]
